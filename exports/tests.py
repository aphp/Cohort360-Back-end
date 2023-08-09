import random
from datetime import timedelta
from typing import List
from unittest import mock
from unittest.mock import MagicMock

from django.utils import timezone
from requests import Response, HTTPError, RequestException
from rest_framework import status
from rest_framework.test import force_authenticate

from accesses.models import Access, Role, Perimeter
from admin_cohort.types import JobStatus, MissingDataError
from admin_cohort.models import User
from admin_cohort.tools.tests_tools import new_user_and_profile, ViewSetTestsWithBasicPerims, random_str, CreateCase, \
    CaseRetrieveFilter, ListCase, RequestCase, RetrieveCase, PatchCase, DeleteCase
from admin_cohort.tools import prettify_json
from cohort.models import CohortResult, RequestQuerySnapshot, Request, DatedMeasure, Folder
from workspaces.models import Account
from .conf_exports import create_hive_db, prepare_hive_db, wait_for_hive_db_creation_job, get_job_status
from .models import ExportRequest, ExportRequestTable
from .tasks import delete_export_requests_csv_files, wait_for_export_job, launch_request
from .types import ExportType, ApiJobResponse
from .views import ExportRequestViewSet

EXPORTS_URL = "/exports"


class ObjectView(object):
    def __init__(self, d):
        self.__dict__ = d


"""
Cas à tester POST export_request:
- si output_format est csv:
  - le provider_id doit être vide ou bien égal à celui du user qui crée
  - il faut que le provider ait créé la cohorte
  - actuellement, le status réponse doit être validated
- si output_format est hive:
  - il faut provider_id
  - en attendant url FHIR plus ouverte : il faut que provider_id = user_id
  - il faut target_unix_account_id
  - il faut que le provider_id soit lié au target_unix_account (via API infra)
  - il faut que le provider ait créé la cohorte
  - si provider_id != user_id : il faut que le user ait accès
    right_review_transfer_jupyter
  - il faut que le provider ait accès read nomi/pseudo (demande FHIR)
    et right_transfer_jupyter_nominative

  - si le user (créateur de la requête) a le droit
  right_review_transfer_jupyter:
    - le status réponse doit être validated
    - sinon, le status est à new

Cas à tester pour GET /exports/users :
  - réponse contient ses propres users (Account, dans workspaces)
  - réponse de liste complète si le user a right_review_transfer_jupyter
  - permet filtre par provider_id : renvoie, grâce à l'API FHIR,
    uniquement les users unix liés au provider_id

Cas à tester pour GET /exports/cohorts :
  - réponse contient les cohortes de l'utilisateur
  - réponse de liste complète si le user a right_review_transfer_jupyter

Cas à tester pour PATCH /exports/{id} :
  - renvoie 403
  - réussit seulement si on a /deny ou /validate dans l'url, si la requête
    est en status created, si le user a right_review_transfer_jupyter
"""

REGEX_TEST_EMAIL = r"^[\w.+-]+@test\.com$"
END_TEST_EMAIL = "@test.com"


def new_cohort_result(owner: User, status: JobStatus = JobStatus.finished,
                      folder: Folder = None, req: Request = None,
                      rqs: RequestQuerySnapshot = None, dm: DatedMeasure = None) -> (Folder, Request, RequestQuerySnapshot, DatedMeasure,
                                                                                     CohortResult):
    perimeter = Perimeter.objects.first()

    if not folder:
        folder: Folder = Folder.objects.create(owner=owner, name=random_str(5))

    if not req:
        req: Request = Request.objects.create(owner=owner,
                                              parent_folder=folder,
                                              name=random_str(5))
    if not rqs:
        rqs: RequestQuerySnapshot = RequestQuerySnapshot.objects.create(owner=owner,
                                                                        request=req,
                                                                        perimeters_ids=[str(perimeter.id)])

    if not dm:
        dm: DatedMeasure = DatedMeasure.objects.create(owner=owner, request_query_snapshot=rqs)
    cr: CohortResult = CohortResult.objects.create(owner=owner,
                                                   fhir_group_id=str(random.randint(0, 10000)),
                                                   dated_measure=dm,
                                                   request_query_snapshot=rqs,
                                                   request_job_status=status)
    return folder, req, rqs, dm, cr


# class GetCase(RequestCase):
#     def __init__(self, user: Union[User, None], status: int,
#                  url: str = EXPORTS_URL, params: Dict = None,
#                  to_find: List[ExportRequest] = None, page_size: int = 100):
#         super(GetCase, self).__init__(user=user, status=status)
#         self.url = url
#         self.params = params
#         self.to_find = to_find
#         self.page_size = page_size


class ExportsTests(ViewSetTestsWithBasicPerims):
    unsettable_default_fields = dict(
        is_user_notified=False,
    )
    unsettable_fields = [
        "id", "execution_request_datetime",
        "is_user_notified", "target_location", "target_name",
        "creator_fk", "cleaned_at", "request_job_id",
        "request_job_status", "request_job_status", "request_job_fail_msg",
        "request_job_duration", "review_request_datetime", "reviewer_fk",
        "insert_datetime", "update_datetime", "delete_datetime",
    ]
    table_unsettable_fields = [
        "source_table_name", "export_request",
        "export_request_table_id"
    ]

    objects_url = "/exports/"
    retrieve_view = ExportRequestViewSet.as_view({'get': 'retrieve'})
    list_view = ExportRequestViewSet.as_view({'get': 'list'})
    create_view = ExportRequestViewSet.as_view({'post': 'create'})
    delete_view = ExportRequestViewSet.as_view({'delete': 'destroy'})
    update_view = ExportRequestViewSet.as_view({'patch': 'partial_update'})
    model = ExportRequest
    model_objects = ExportRequest.objects
    model_fields = ExportRequest._meta.fields

    def setUp(self):
        super(ExportsTests, self).setUp()

        # ROLES
        (self.role_review_csv,
         self.role_review_jupyter,
         self.role_read_pseudo,
         self.role_read_nomi,
         self.role_exp_csv_pseudo,
         self.role_exp_csv_nomi,
         self.role_exp_jup_pseudo,
         self.role_exp_jup_nomi) = [
            Role.objects.create(**dict([
                (f, f == right) for f in self.all_rights]), name=name)
            for (name, right) in [
                ("REVIEW_CSV", "right_review_export_csv"),
                ("REVIEW_JUPYTER", "right_review_transfer_jupyter"),
                ("READ_PSEUDO", "right_read_patient_pseudo_anonymised"),
                ("READ_NOMI", "right_read_patient_nominative"),
                ("EXP_CSV_PSEUDO", "right_export_csv_pseudo_anonymised"),
                ("EXP_CSV_NOMI", "right_export_csv_nominative"),
                ("EXP_JUP_PSEUDO", "right_transfer_jupyter_pseudo_anonymised"),
                ("EXP_JUP_NOMI", "right_transfer_jupyter_nominative"),
            ]]

        # USERS
        self.user_with_no_right, ph_with_no_right = new_user_and_profile(
            email=f"with_no_right{END_TEST_EMAIL}")
        self.user_jup_reviewer, self.ph_jup_reviewer = new_user_and_profile(
            email=f"jup_reviewer{END_TEST_EMAIL}")
        self.user_csv_reviewer, ph_csv_reviewer = new_user_and_profile(
            email=f"csv_reviewer{END_TEST_EMAIL}")

        self.user1, self.prof_1 = new_user_and_profile(
            email=f"us1{END_TEST_EMAIL}")
        self.user2, self.prof_2 = new_user_and_profile(
            email=f"us2{END_TEST_EMAIL}")

        # ACCESSES
        self.jup_review_access: Access = Access.objects.create(
            perimeter=self.aphp, role=self.role_review_jupyter,
            profile=self.ph_jup_reviewer)

        self.csv_review_access: Access = Access.objects.create(
            perimeter=self.aphp, role=self.role_review_csv,
            profile=ph_csv_reviewer)

        self.user1_nomi_acc: Access = Access.objects.create(
            perimeter=self.aphp,
            profile=self.prof_1,
            role=self.role_read_nomi
        )

        # COHORTS
        _, _, _, _, self.user1_cohort = new_cohort_result(owner=self.user1,
                                                          status=JobStatus.finished.value)

        _, _, _, _, self.user2_cohort = new_cohort_result(owner=self.user2,
                                                          status=JobStatus.finished.value)

    def check_is_created(self, base_instance: ExportRequest,
                         request_model: dict = None, user: User = None):
        if user is None:
            self.fail("There should be user provided")

        super(ExportsTests, self).check_is_created(base_instance, request_model)
        self.assertEqual(base_instance.creator_fk.pk, user.pk)

        for table in request_model.get("tables", []):
            ert = ExportRequestTable.objects.filter(
                omop_table_name=table.get("omop_table_name", ""),
                export_request=base_instance
            ).first()
            self.assertIsNotNone(ert)

            [self.assertNotEqual(
                getattr(ert, f), table.get(f),
                f"Error with model's table's {f}"
            ) for f in self.table_unsettable_fields if f in table]

    def check_list_reqs(self, found: List[ExportRequest],
                        to_find: List[ExportRequest], key: str = ""):
        msg = f"{key} What was to find: \n {[r for r in to_find]}.\n " \
              f"What was found: \n {[r for r in found]}"
        self.assertEqual(len(to_find), len(found), msg)
        found_ids = [er.get("export_request_id", "") for er in found]
        [
            self.assertIn(er.id, found_ids,
                          f"{msg}.\nMissing request is {er}")
            for er in to_find]


class ExportsWithSimpleSetUp(ExportsTests):
    def setUp(self):
        super(ExportsWithSimpleSetUp, self).setUp()

        self.user1_exp_req_succ: ExportRequest = \
            ExportRequest.objects.create(
                owner=self.user1,
                creator_fk=self.user1,
                cohort_fk=self.user1_cohort,
                cohort_id=42,
                output_format=ExportType.CSV.value,
                provider_id=self.user1.provider_id,
                request_job_status=JobStatus.finished,
                target_location="user1_exp_req_succ",
                is_user_notified=False,
            )
        self.user1_exp_req_succ_table1: ExportRequestTable = \
            ExportRequestTable.objects.create(
                export_request=self.user1_exp_req_succ,
                omop_table_name="Hello",
            )

        self.user1_exp_req_fail: ExportRequest = \
            ExportRequest.objects.create(
                owner=self.user1,
                cohort_fk=self.user1_cohort,
                cohort_id=42,
                output_format=ExportType.CSV.value,
                provider_id=self.user1.provider_id,
                request_job_status=JobStatus.failed.value,
                target_location="user1_exp_req_failed",
                is_user_notified=False,
            )

        self.user2_exp_req_succ: ExportRequest = \
            ExportRequest.objects.create(
                owner=self.user2,
                cohort_fk=self.user2_cohort,
                cohort_id=43,
                output_format=ExportType.CSV.value,
                provider_id=self.user1.provider_id,
                request_job_status=JobStatus.finished.value,
                target_location="user2_exp_req_succ",
                is_user_notified=True,
            )
        #
        # self.user2_exp_req_table: ExportRequestTable = \
        #     ExportRequestTable.objects.create(
        #         export_request=self.user2_exp_req,
        #         omop_table_name="Hello",
        #     )


# GET ##################################################################


class ExportsListTests(ExportsTests):
    def setUp(self):
        super(ExportsListTests, self).setUp()

        _, _, _, _, self.user1_cohort2 = new_cohort_result(
            self.user1, JobStatus.finished
        )
        f, r, rqs, dm, self.user2_cohort_1 = new_cohort_result(
            owner=self.user2, status=JobStatus.finished)
        _, _, _, _, self.user2_cohort2 = new_cohort_result(
            self.user2, JobStatus.finished, f, r, rqs, dm
        )

        self.user1_unix_acc: Account = Account.objects.create(
            username='user1', spark_port_start=0)

        example_int = 42
        self.user1_reqs = ExportRequest.objects.bulk_create([
            ExportRequest(
                owner=self.user1,
                cohort_fk=random.choice([
                    self.user1_cohort,
                    self.user1_cohort2,
                ]),
                cohort_id=example_int,
                nominative=random.random() > 0.5,
                shift_dates=random.random() > 0.5,
                target_unix_account=self.user1_unix_acc,
                output_format=random.choice([ExportType.CSV.value,
                                             ExportType.HIVE.value]),
                provider_id=self.user1.provider_id,
                request_job_status=random.choice([
                    JobStatus.new.value, JobStatus.failed.value,
                    JobStatus.validated.value]),
                target_location=f"test_user_rec_{str(i)}",
                is_user_notified=False,
            ) for i in range(0, 200)
        ])

        self.user2_reqs: List[ExportRequest] = \
            ExportRequest.objects.bulk_create([
                ExportRequest(
                    cohort_fk=random.choice([
                        self.user1_cohort,
                        self.user1_cohort2,
                    ]),
                    cohort_id=example_int,
                    output_format=random.choice([ExportType.CSV.value,
                                                 ExportType.HIVE.value]),
                    provider_id=self.user2.provider_id,
                    owner=self.user2,
                    request_job_status=random.choice([
                        JobStatus.new.value, JobStatus.failed.value,
                        JobStatus.validated.value]),
                    target_location=f"test_user2_{str(i)}",
                    is_user_notified=False,
                ) for i in range(0, 200)
            ])

    def test_list_requests_as_jup_reviewer(self):
        base_results = self.user1_reqs + self.user2_reqs

        self.check_get_paged_list_case(ListCase(to_find=[e for e in base_results if e.output_format == ExportType.HIVE],
                                                page_size=20,
                                                user=self.user_jup_reviewer,
                                                status=status.HTTP_200_OK,
                                                success=True,
                                                params={"output_format": ExportType.HIVE}))

    def test_list_requests_as_csv_reviewer(self):
        base_results = self.user1_reqs + self.user2_reqs

        self.check_get_paged_list_case(ListCase(to_find=[e for e in base_results if e.output_format == ExportType.CSV],
                                                page_size=20,
                                                user=self.user_csv_reviewer,
                                                status=status.HTTP_200_OK,
                                                success=True,
                                                params={"output_format": ExportType.CSV}))

    def test_list_requests_as_user1(self):
        base_results = self.user1_reqs

        self.check_get_paged_list_case(ListCase(to_find=base_results,
                                                page_size=20,
                                                user=self.user1,
                                                status=status.HTTP_200_OK,
                                                success=True,
                                                params={"owner": self.user1.pk}))

    def test_list_requests_as_full_reviewer_with_filters(self):
        # As a user with right_read_admin_accesses_same_level on a
        # care_site, I can get accesses on the same care_site and whom
        # the role has admin rights, and only them

        # we also give right to review csv exports to jupyter reviewer
        Access.objects.create(
            perimeter=self.aphp,
            role=self.role_review_csv,
            profile=self.ph_jup_reviewer,
        )

        base_results = self.user1_reqs + self.user2_reqs
        param_cases = {
            'output_format': {
                'value': ExportType.CSV.value,
                'to_find': [
                    e for e in base_results
                    if e.output_format == ExportType.CSV.value
                ]
            },
            'request_job_status': {
                'value': JobStatus.new.value,
                'to_find': [
                    e for e in base_results
                    if e.request_job_status == JobStatus.new
                ]
            },
        }

        for (param, pc) in param_cases.items():
            pcs = [pc] if not isinstance(pc, list) else pc
            for pc_ in pcs:
                param_cases = [
                    {**pc_, 'value': v} for v in pc_['value']
                ] if isinstance(pc_['value'], list) else [pc_]

                [
                    self.check_get_paged_list_case(ListCase(
                        params=dict({param: p_case['value']}),
                        to_find=p_case['to_find'],
                        page_size=20,
                        user=self.user_jup_reviewer,
                        status=status.HTTP_200_OK,
                        success=True
                    )) for p_case in param_cases
                ]


class DownloadCase(RequestCase):
    def __init__(self, data_to_download: dict, mock_hdfs_resp: any = None,
                 mock_file_size_resp: any = None, mock_hdfs_called: bool = True,
                 mock_file_size_called: bool = True, **kwargs):
        self.data_to_download = data_to_download or dict()
        self.mock_hdfs_resp = mock_hdfs_resp
        self.mock_file_size_resp = mock_file_size_resp
        self.mock_hdfs_called = mock_hdfs_called
        self.mock_file_size_called = mock_file_size_called
        super(DownloadCase, self).__init__(**kwargs)


class ExportsRetrieveTests(ExportsWithSimpleSetUp):
    download_view = ExportRequestViewSet.as_view({'get': 'download'})

    def setUp(self):
        super(ExportsRetrieveTests, self).setUp()
        self.base_data = dict(
            owner=self.user1,
            cohort_fk=self.user1_cohort,
            cohort_id=42,
            output_format=ExportType.CSV.value,
            provider_id=self.user1.provider_id,
            request_job_status=JobStatus.finished.value,
            target_location="location_example",
            is_user_notified=False,
        )
        self.base_download_case: DownloadCase = DownloadCase(
            mock_hdfs_resp=[""], mock_file_size_resp=1,
            mock_hdfs_called=True, mock_file_size_called=True,
            user=self.user1,
            data_to_download=self.base_data,
            success=True,
            status=status.HTTP_200_OK,
        )
        self.base_err_download_case = self.base_download_case.clone(
            success=False,
            status=status.HTTP_403_FORBIDDEN,
            mock_file_size_called=False,
            mock_hdfs_called=False,
        )

    def test_get_request_as_owner(self):
        # As a user, I can retrieve an ExportRequest I created
        self.check_retrieve_case(RetrieveCase(
            to_find=self.user1_exp_req_succ,
            view_params=dict(id=self.user1_exp_req_succ.id),
            status=status.HTTP_200_OK,
            user=self.user1,
            success=True,
        ))

    def test_get_request_as_csv_reviewer(self):
        # As a Csv export reviewer, I can retrieve a CSV ExportRequest
        # from another user
        self.check_retrieve_case(RetrieveCase(
            to_find=self.user2_exp_req_succ,
            view_params=dict(id=self.user2_exp_req_succ.id),
            status=status.HTTP_200_OK,
            user=self.user_csv_reviewer,
            success=True,
        ))

    def test_error_get_request_not_owner(self):
        # As a simple user, I cannot retrieve another user's ExportRequest
        self.check_retrieve_case(RetrieveCase(
            to_find=self.user2_exp_req_succ,
            view_params=dict(id=self.user2_exp_req_succ.id),
            status=status.HTTP_404_NOT_FOUND,
            user=self.user1,
            success=False,
        ))

    @mock.patch('exports.conf_exports.stream_gen')
    @mock.patch('exports.conf_exports.get_file_size')
    def check_download(self, case: DownloadCase, mock_get_file_size: MagicMock,
                       mock_hdfs_stream_gen: MagicMock):
        mock_hdfs_stream_gen.return_value = case.mock_hdfs_resp
        mock_get_file_size.return_value = case.mock_file_size_resp

        obj = self.model_objects.create(**case.data_to_download)

        request = self.factory.get(self.objects_url)

        if case.user:
            force_authenticate(request, case.user)
        response = self.__class__.download_view(request, id=obj.pk)
        try:
            response.render()
            msg = (f"{case.title}: "
                   + prettify_json(str(response.content))
                   if response.content else "")
        except Exception:
            msg = (f"{case.title}: "
                   + prettify_json(str(response.reason_phrase))
                   if response.reason_phrase else "")

        self.assertEqual(response.status_code, case.status, msg=msg)

        if case.success:
            self.assertEquals(
                response.get('Content-Disposition'),
                f"attachment; filename=export_"
                f"{obj.cohort_id}.zip"
            )
            self.assertEquals(response.get('Content-length'), '1')
        else:
            self.assertNotEqual(
                response.get('Content-Disposition'),
                f"attachment; filename=export_"
                f"{obj.cohort_id}.zip"
            )
            self.assertNotEqual(response.get('Content-length'), '1')

        mock_hdfs_stream_gen.assert_called_once() if case.mock_hdfs_called \
            else mock_hdfs_stream_gen.assert_not_called()
        mock_get_file_size.assert_called_once() if case.mock_file_size_called \
            else mock_get_file_size.assert_not_called()

    def test_download_request_result(self):
        # As a user, I can download the result of an ExportRequest I created
        self.check_download(self.base_download_case)

    def test_error_download_request_not_finished(self):
        # As a user, I cannot download the result of
        # an ExportRequest that is not finished
        [self.check_download(self.base_err_download_case.clone(
            data_to_download={**self.base_data,
                              'request_job_status': s},
        )) for s in JobStatus.list(exclude=[JobStatus.finished])]

    def test_error_download_request_not_csv(self):
        # As a user, I cannot download the result of an ExportRequest that is
        # not of type CSV and with job status finished
        self.check_download(self.base_err_download_case.clone(
            data_to_download={**self.base_data,
                              'output_format': ExportType.HIVE},
            status=status.HTTP_403_FORBIDDEN,
        ))

    def test_error_download_request_result_not_owned(self):
        # As a user, I can download the result of another user's ExportRequest
        self.check_download(self.base_err_download_case.clone(
            data_to_download={**self.base_data, 'owner': self.user2},
            status=status.HTTP_404_NOT_FOUND,
        ))

# JOBS ##################################################################


class ExportsJobsTests(ExportsWithSimpleSetUp):

    @mock.patch('exports.emails.send_email')
    @mock.patch('exports.conf_exports.delete_file')
    def test_task_delete_export_requests_csv_files(self, mock_delete_hdfs_file, mock_send_email):
        from admin_cohort.settings import DAYS_TO_DELETE_CSV_FILES

        mock_delete_hdfs_file.return_value = None
        mock_send_email.return_value = None

        self.user1_exp_req_succ.review_request_datetime = (
                timezone.now() - timedelta(days=DAYS_TO_DELETE_CSV_FILES))
        self.user1_exp_req_succ.is_user_notified = True
        self.user1_exp_req_succ.save()

        delete_export_requests_csv_files()

        deleted_ers = list(ExportRequest.objects.filter(cleaned_at__isnull=False))

        self.assertCountEqual([er.pk for er in deleted_ers], [self.user1_exp_req_succ.pk])
        [self.assertAlmostEqual((er.cleaned_at - timezone.now()).total_seconds(), 0, delta=1) for er in deleted_ers]

    @mock.patch('exports.emails.send_email')
    @mock.patch('exports.conf_exports.prepare_hive_db')
    @mock.patch('exports.conf_exports.post_export')
    @mock.patch('exports.conf_exports.conclude_export_hive')
    @mock.patch('exports.conf_exports.get_job_status')
    def test_task_launch_request(self, mock_get_job_status, mock_prepare_hive_db, mock_post_export, mock_conclude_export_hive, mock_send_email):
        mock_get_job_status.return_value = ApiJobResponse(status=JobStatus.finished)
        mock_prepare_hive_db.return_value = None
        mock_post_export.return_value = None
        mock_conclude_export_hive.return_value = None
        mock_send_email.return_value = None

        launch_request(er_id=self.user1_exp_req_succ.id)

        mock_get_job_status.assert_called()
        mock_prepare_hive_db.assert_not_called()
        mock_post_export.assert_called()
        mock_conclude_export_hive.assert_not_called()
        mock_send_email.assert_called()


# POST ##################################################################


class ExportCaseRetrieveFilter(CaseRetrieveFilter):
    def __init__(self, motivation: str, exclude: dict = None):
        self.motivation = motivation

        super(ExportCaseRetrieveFilter, self).__init__(exclude=exclude)


class ExportCreateCase(CreateCase):
    def __init__(self, job_status: str, mock_email_failed: bool, **kwargs):
        super(ExportCreateCase, self).__init__(**kwargs)
        self.job_status = job_status
        self.mock_email_failed = mock_email_failed


class ExportJupyterCreateCase(ExportCreateCase):
    def __init__(self, mock_user_bound_resp: bool,
                 mock_user_bound_called: bool, **kwargs):
        self.mock_user_bound_resp = mock_user_bound_resp
        self.mock_user_bound_called = mock_user_bound_called
        super(ExportJupyterCreateCase, self).__init__(**kwargs)


class ExportsCreateTests(ExportsTests):
    @mock.patch('exports.tasks.launch_request.delay')
    @mock.patch('exports.emails.send_email')
    @mock.patch('exports.emails.EMAIL_REGEX_CHECK', REGEX_TEST_EMAIL)
    def check_create_case(self, case: ExportCreateCase, mock_send_email: MagicMock, mock_task: MagicMock):
        mock_task.return_value = None
        mock_send_email.return_value = None

        super(ExportsCreateTests, self).check_create_case(case)

        mock_send_email.assert_called() if case.success else mock_send_email.assert_not_called()
        mock_task.assert_called() if case.success else mock_task.assert_not_called()


class ExportsCsvCreateTests(ExportsCreateTests):
    def setUp(self):
        super(ExportsCsvCreateTests, self).setUp()

        self.user1_csv_nomi_acc: Access = Access.objects.create(
            perimeter=self.aphp,
            profile=self.prof_1,
            role=self.role_exp_csv_nomi
        )

        basic_export_descr = "basic_export"
        self.basic_data = dict(
            output_format=ExportType.CSV.value,
            nominative=True,
            shift_dates=False,
            tables=[dict(omop_table_name="provider")],
            cohort_fk=self.user1_cohort.pk,
            motivation=basic_export_descr,
        )
        self.basic_case = ExportCreateCase(
            data=self.basic_data,
            user=self.user1,
            status=status.HTTP_201_CREATED,
            success=True,
            retrieve_filter=ExportCaseRetrieveFilter(
                motivation=basic_export_descr),
            mock_email_failed=False,
            job_status=JobStatus.validated,
        )
        self.err_basic_case = self.basic_case.clone(
            success=False,
            mock_email_called=False,
        )

    def test_create_csv_full_request(self):
        # As a provider with right to read nominative data and export csv
        # I can create an export_request with unsettables fields that won't be
        # set
        example_date = timezone.now() + timedelta(minutes=10)
        example_str = "test"
        example_user = self.user_with_no_right
        example_int = 50
        cases = [self.basic_case, self.basic_case.clone(
            # complete case
            data={
                **self.basic_data,
                **dict(
                    tables=[
                        dict(
                            omop_table_name="provider",
                            source_table_name="test",  # unsettable
                            target_table_name="test",  # unsettable
                            export_request=444,  # unsettable
                            export_request_table_id=3333,  # unsettable
                        ),
                    ],
                    id=example_int,
                    execution_request_datetime=example_date,
                    validation_request_datetime=example_date,
                    is_user_notified=True,
                    target_location=example_str,
                    target_name=example_str,
                    creator_id=example_user.pk,
                    reviewer_id=example_user.pk,
                    cleaned_at=example_date,
                    insert_datetime=example_date,
                    update_datetime=example_date,
                    delete_datetime=example_date,
                    request_job_id=example_int,
                    request_job_status=example_str,
                    request_job_fail_msg=example_str,
                    request_job_duration=example_int,
                    review_request_datetime=example_date,
                    reviewer_fk=example_user.pk,
                )
            },
            job_status=JobStatus.validated.value,
            success=True,
            user=self.user1,
        )]

        [self.check_create_case(case) for case in cases]

    def test_error_create_request_no_email(self):
        # As a user, I cannot create an export request if the recipient has no
        # email address
        self.user1.email = ""
        self.user1.save()

        case = self.err_basic_case.clone(
            user=self.user1,
            status=status.HTTP_400_BAD_REQUEST,
        )
        self.check_create_case(case)

    def test_error_create_cohort_not_owned(self):
        # As a user, I cannot create an export request
        # if I do not own the targeted cohort
        case = self.err_basic_case.clone(
            data={**self.basic_data, 'cohort_fk': self.user2_cohort.uuid},
            created=False,
            user=self.user1,
            status=status.HTTP_400_BAD_REQUEST,
        )
        self.check_create_case(case)

    def test_error_create_csv_other_user_cohort_not_owned(self):
        # As a user, I cannot create an export request for a cohort I don't own
        case = self.err_basic_case.clone(
            data={**self.basic_data},
            created=False,
            user=self.user2,
            status=status.HTTP_400_BAD_REQUEST,
        )
        self.check_create_case(case)

    def test_error_create_csv_pseudo(self):
        # I cannot create an export request with Pseudonym mode
        case = self.err_basic_case.clone(
            data={**self.basic_data, 'nominative': False},
            created=False,
            status=status.HTTP_400_BAD_REQUEST,
        )
        self.check_create_case(case)


class ExportsJupyterCreateTests(ExportsCreateTests):
    def setUp(self):
        super(ExportsJupyterCreateTests, self).setUp()

        self.user1_jup_nomi_acc: Access = Access.objects.create(
            perimeter=self.aphp,
            profile=self.prof_1,
            role=self.role_exp_jup_nomi
        )
        self.user2_nomi_acc: Access = Access.objects.create(
            perimeter=self.aphp,
            profile=self.prof_2,
            role=self.role_read_nomi
        )
        self.user2_jup_nomi_acc: Access = Access.objects.create(
            perimeter=self.aphp,
            profile=self.prof_2,
            role=self.role_exp_jup_nomi
        )

        self.user1_unix_acc: Account = Account.objects.create(
            username='user1', spark_port_start=0)

        basic_export_descr = "basic_export"
        self.basic_data = dict(
            output_format=ExportType.HIVE.value,
            nominative=True,
            shift_dates=False,
            tables=[dict(omop_table_name="provider")],
            cohort_fk=self.user1_cohort.pk,
            motivation=basic_export_descr,
            # actual validity will be returned by mock
            target_unix_account=self.user1_unix_acc.pk,
        )
        self.basic_case = ExportJupyterCreateCase(
            data=self.basic_data,
            user=self.user1,
            status=status.HTTP_201_CREATED,
            success=True,
            retrieve_filter=ExportCaseRetrieveFilter(
                motivation=basic_export_descr),
            mock_email_failed=False,
            job_status=JobStatus.validated,
            mock_user_bound_resp=True,
            mock_user_bound_called=True,
        )
        self.err_basic_case = self.basic_case.clone(
            success=False,
            mock_email_called=False,
            mock_user_bound_called=False,
        )

        self.export_request = ExportRequest.objects.create(owner=self.user1,
                                                           cohort_fk=self.user1_cohort,
                                                           cohort_id=self.user1_cohort.fhir_group_id,
                                                           nominative=True,
                                                           shift_dates=True,
                                                           target_unix_account=self.user1_unix_acc,
                                                           output_format=ExportType.HIVE.value,
                                                           provider_id=self.user1.provider_id,
                                                           target_name="user1_12345",
                                                           target_location="test/user/exports")

    @mock.patch('workspaces.conf_workspaces.is_user_bound_to_unix_account')
    def check_create_case(self, case: ExportJupyterCreateCase,
                          mock_user_bound: MagicMock):
        mock_user_bound.return_value = case.mock_user_bound_resp
        super(ExportsJupyterCreateTests, self).check_create_case(case)
        mock_user_bound.assert_called() if case.mock_user_bound_called \
            else mock_user_bound.assert_not_called()

    def test_create_jup_full_request(self):
        # As a provider with right to read nominative data and export csv
        # I can create an export_request with unsettables fields that won't be
        # set
        example_date = timezone.now() + timedelta(minutes=10)
        example_str = "test"
        example_user = self.user_with_no_right
        example_int = 50
        cases = [self.basic_case, self.basic_case.clone(
            # complete case
            data={
                **self.basic_data,
                **dict(
                    tables=[
                        dict(
                            omop_table_name="provider",
                            source_table_name="test",  # unsettable
                            target_table_name="test",  # unsettable
                            export_request=444,  # unsettable
                            export_request_table_id=3333,  # unsettable
                        ),
                    ],
                    id=example_int,
                    execution_request_datetime=example_date,
                    validation_request_datetime=example_date,
                    is_user_notified=True,
                    target_location=example_str,
                    target_name=example_str,
                    creator_id=example_user.pk,
                    reviewer_id=example_user.pk,
                    cleaned_at=example_date,
                    insert_datetime=example_date,
                    update_datetime=example_date,
                    delete_datetime=example_date,
                    request_job_id=example_int,
                    request_job_status=example_str,
                    request_job_fail_msg=example_str,
                    request_job_duration=example_int,
                    review_request_datetime=example_date,
                    reviewer_fk=example_user.pk,
                )
            },
            job_status=JobStatus.validated,
            success=True,
            user=self.user1,
        )]

        [self.check_create_case(case) for case in cases]

    def test_create_jup_other_recipient_with_rev_access(self):
        # As a user with right to review jupyter exports,
        # I can create an export request with a cohort from another user
        # to a Unix account owned by a third user
        self.check_create_case(self.basic_case.clone(
            data={**self.basic_data,
                  'cohort_fk': self.user1_cohort.pk,
                  'owner': self.user2.pk},
            mock_user_bound_called=False,
            user=self.user_jup_reviewer,
        ))

    def test_create_jup_no_owner_with_rev_access(self):
        # As a user with right to review jupyter exports,
        # I can create an export request with a cohort from another user
        # without providing owner (will be me by default)
        self.check_create_case(self.basic_case.clone(
            data={**self.basic_data,
                  'cohort_fk': self.user2_cohort.pk},
            mock_user_bound_resp=False,
            mock_user_bound_called=False,
            user=self.user_jup_reviewer,
            created=True,
            status=status.HTTP_201_CREATED,
        ))

    def test_error_create_jup_not_owned_cohort_without_rev_access(self):
        # As a user, I cannot create an export request for a cohort I don't own
        self.check_create_case(self.err_basic_case.clone(
            data={**self.basic_data, 'cohort_fk': self.user2_cohort.pk},
            created=False,
            status=status.HTTP_400_BAD_REQUEST,
        ))

    def test_error_create_jup_other_recipient_without_rev_access(self):
        # As a user, I cannot create an export request for another owner
        self.check_create_case(self.err_basic_case.clone(
            data={**self.basic_data},
            created=False,
            user=self.user2,
            status=status.HTTP_400_BAD_REQUEST,
        ))

    def test_error_create_request_no_email(self):
        # As a user, I cannot create an export request if the owner has no
        # email address
        self.user1.email = ""
        self.user1.save()

        self.check_create_case(
            self.err_basic_case.clone(status=status.HTTP_400_BAD_REQUEST))

    def test_error_create_request_wrong_email(self):
        # As a user, I cannot create an export request if the owner has no
        # email address
        self.user1.email = f"us1{END_TEST_EMAIL}m"
        self.user1.save()

        self.check_create_case(
            self.err_basic_case.clone(status=status.HTTP_400_BAD_REQUEST))

    def test_error_create_cohort_unfound(self):
        self.check_create_case(self.err_basic_case.clone(
            data={**self.basic_data, 'cohort_fk': 9999},
            created=False,
            status=status.HTTP_400_BAD_REQUEST,
        ))

    def test_error_create_jup_no_unix_account(self):
        # As a user, I cannot create an export request
        # if I am not bound to the target unix account
        cases = [self.err_basic_case.clone(
            created=False,
            status=status.HTTP_400_BAD_REQUEST,
            mock_user_bound_resp=False,
            mock_user_bound_called=True,
        )]
        [self.check_create_case(case) for case in cases]

    def test_error_create_without_jup_nomi_right(self):
        # As a user, I cannot create a nominative export request
        # without the right to do it

        # we close the access that should allow reviewer to review exports
        self.user1_jup_nomi_acc.manual_end_datetime = \
            timezone.now() - timedelta(days=2)
        self.user1_jup_nomi_acc.save()

        self.check_create_case(self.err_basic_case.clone(
            created=False,
            status=status.HTTP_400_BAD_REQUEST,
            mock_user_bound_called=True,
        ))

    @mock.patch("exports.conf_exports.change_hive_db_ownership")
    @mock.patch("exports.conf_exports.create_hive_db")
    def test_prepare_hive_db(self, mock_create_hive_db, mock_change_hive_db_ownership):
        prepare_hive_db(export_request=self.export_request)
        mock_create_hive_db.assert_called()
        mock_change_hive_db_ownership.assert_called()

    @mock.patch("exports.conf_exports.wait_for_hive_db_creation_job")
    @mock.patch("exports.conf_exports.requests.post")
    def test_create_hive_db(self, mock_request_post, mock_wait_for_hive_db):
        resp = Response()
        resp.status_code = 200
        resp._content = b'{"task_id": "random_task_id"}'
        mock_request_post.return_value = resp
        create_hive_db(export_request=self.export_request)
        mock_wait_for_hive_db.assert_called()

    @mock.patch("exports.conf_exports.requests.post")
    def test_create_hive_db_with_bad_status_code(self, mock_request_post):
        resp = Response()
        resp.status_code = 503
        mock_request_post.return_value = resp
        with self.assertRaises(RequestException):
            create_hive_db(export_request=self.export_request)

    @mock.patch("exports.conf_exports.requests.post")
    def test_create_hive_db_with_missing_data(self, mock_request_post):
        resp = Response()
        resp.status_code = 200
        resp._content = b'{}'
        mock_request_post.return_value = resp
        with self.assertRaises(MissingDataError):
            create_hive_db(export_request=self.export_request)

    @mock.patch("exports.conf_exports.get_job_status")
    @mock.patch("exports.conf_exports.time.sleep")
    def test_wait_for_hive_db_creation_job(self, mock_sleep, mock_get_job_status):
        mock_sleep.return_value = None
        mock_get_job_status.return_value = ApiJobResponse(status=JobStatus.finished)
        result = wait_for_hive_db_creation_job(job_id="random_task_id")
        self.assertIsNone(result)

    @mock.patch("exports.conf_exports.get_job_status")
    @mock.patch("exports.conf_exports.time.sleep")
    def test_failure_on_wait_for_hive_db_creation_job(self, mock_sleep, mock_get_job_status):
        mock_sleep.return_value = None
        mock_get_job_status.return_value = ApiJobResponse(status=JobStatus.failed)
        with self.assertRaises(HTTPError):
            wait_for_hive_db_creation_job(job_id="random_task_id")

    @mock.patch("exports.conf_exports.requests.get")
    def test_get_job_status(self, mock_requests_get):
        resp = Response()
        resp.status_code = 200
        resp._content = b'{"task_status": "PENDING", "task_result": null}'
        mock_requests_get.return_value = resp
        job_status = get_job_status(service="hadoop", job_id="random_task_id")
        self.assertEqual(job_status.status, JobStatus.pending.value)
        self.assertEqual(job_status.output, "")
        self.assertEqual(job_status.err, "")

    @mock.patch("exports.conf_exports.requests.get")
    def test_get_job_status_with_unknown_status(self, mock_requests_get):
        resp = Response()
        resp.status_code = 200
        resp._content = b'{"task_status": "WRONG", "task_result": {"status": "WRONG", "ret_code": "0", "err": "error", "out": "out"}}'
        mock_requests_get.return_value = resp
        job_status = get_job_status(service="hadoop", job_id="random_task_id")
        self.assertEqual(job_status.status, JobStatus.unknown.value)
        self.assertEqual(job_status.output, "out")
        self.assertNotEqual(job_status.err, "")

    @mock.patch("exports.conf_exports.requests.get")
    def test_get_job_status_with_bad_status_code(self, mock_requests_get):
        resp = Response()
        resp.status_code = 403
        mock_requests_get.return_value = resp
        with self.assertRaises(HTTPError):
            _ = get_job_status(service="hadoop", job_id="random_task_id")

    @mock.patch("exports.conf_exports.requests.get")
    def test_get_job_status_with_missing_data(self, mock_requests_get):
        resp = Response()
        resp.status_code = 200
        resp._content = b'{"task_status": "PENDING"}'
        mock_requests_get.return_value = resp
        with self.assertRaises(MissingDataError):
            _ = get_job_status(service="hadoop", job_id="random_task_id")

    @mock.patch("exports.tasks.conf_exports.get_job_status")
    @mock.patch("exports.tasks.time.sleep")
    def test_wait_for_export_job(self, mock_sleep, mock_get_job_status):
        mock_sleep.return_value = None
        mock_get_job_status.return_value = ApiJobResponse(status=JobStatus.finished)
        wait_for_export_job(er=self.export_request)
        self.assertEqual(self.export_request.request_job_status, JobStatus.finished.value)


class ExportsNotAllowedTests(ExportsWithSimpleSetUp):
    def setUp(self):
        super(ExportsNotAllowedTests, self).setUp()
        self.full_admin_user, full_admin_ph = new_user_and_profile("full@us.er")
        role_full: Role = Role.objects.create(**dict([
            (f, True) for f in self.all_rights
        ]), name='FULL')

        Access.objects.create(role=role_full, profile=full_admin_ph,
                              perimeter=self.aphp)

        self.basic_jup_data = dict(
            owner=self.full_admin_user,
            cohort_fk=self.user1_cohort,
            cohort_id=self.user1_cohort.fhir_group_id,
            output_format=ExportType.HIVE.value,
            provider_id=self.user1.provider_id,
            request_job_status=JobStatus.new.value,
            target_location="user1_exp_req_succ",
            is_user_notified=False,

        )
        self.basic_csv_data = {**self.basic_jup_data,
                               'output_format': ExportType.CSV.value}


class ExportsPatchNotAllowedTests(ExportsNotAllowedTests):
    def test_error_patch_request(self):
        [self.check_patch_case(PatchCase(
            user=self.full_admin_user, status=status.HTTP_405_METHOD_NOT_ALLOWED,
            success=False, initial_data=data, data_to_update={'motivation': 'a'}
        )) for data in [self.basic_csv_data, self.basic_jup_data]]


class ExportsDeleteNotAllowedTests(ExportsNotAllowedTests):
    def test_error_delete_request(self):
        [self.check_delete_case(DeleteCase(
            user=self.full_admin_user,
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
            success=False, data_to_delete=data,
        )) for data in [self.basic_csv_data, self.basic_jup_data]]


class ExportsUpdateNotAllowedTests(ExportsNotAllowedTests):
    update_view = ExportRequestViewSet.as_view({'update': 'update'})

    def test_error_update_request(self):
        [self.check_patch_case(PatchCase(
            user=self.full_admin_user,
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
            success=False, initial_data=data, data_to_update={}
        )) for data in [self.basic_csv_data, self.basic_jup_data]]

#  USERS ##################################################################


class UsersGetTests(ExportsTests):
    pass


#  COHORTS ##################################################################


class CohortsGetTests(ExportsTests):
    pass
