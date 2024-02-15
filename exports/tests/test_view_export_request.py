import random
from datetime import timedelta
from typing import List, Any
from unittest import mock
from unittest.mock import MagicMock

import requests
from django.utils import timezone
from requests import Response, HTTPError, RequestException
from rest_framework import status
from rest_framework.test import force_authenticate

from accesses.models import Access, Role, Perimeter
from admin_cohort.types import JobStatus, MissingDataError
from admin_cohort.models import User
from admin_cohort.tests.tests_tools import new_user_and_profile, ViewSetTestsWithBasicPerims, random_str, CreateCase, \
    CaseRetrieveFilter, ListCase, RequestCase, RetrieveCase, PatchCase, DeleteCase
from admin_cohort.tools import prettify_json
from cohort.models import CohortResult, RequestQuerySnapshot, Request, DatedMeasure, Folder
from workspaces.models import Account
from exports.conf_exports import create_hive_db, prepare_hive_db, wait_for_hive_db_creation_job, get_job_status, ApiJobStatus, JobStatusResponse, \
    wait_for_export_job, mark_export_request_as_failed
from exports.models import ExportRequest, ExportRequestTable, Export, ExportTable, InfrastructureProvider, Datalab
from exports.tasks import delete_export_requests_csv_files, launch_request, launch_export_task
from exports.types import ExportType, ExportStatus
from exports.views import ExportRequestViewSet

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
    right_review_export_jupyter
  - il faut que le provider ait accès read nomi/pseudo (demande FHIR)
    et right_export_jupyter_nominative

  - si le user (créateur de la requête) a le droit
  right_review_export_jupyter:
    - le status réponse doit être validated
    - sinon, le status est à new

Cas à tester pour GET /exports/users :
  - réponse contient ses propres users (Account, dans workspaces)
  - réponse de liste complète si le user a right_review_export_jupyter
  - permet filtre par provider_id : renvoie, grâce à l'API FHIR,
    uniquement les users unix liés au provider_id

Cas à tester pour GET /exports/cohorts :
  - réponse contient les cohortes de l'utilisateur
  - réponse de liste complète si le user a right_review_export_jupyter

Cas à tester pour PATCH /exports/{id} :
  - renvoie 403
  - réussit seulement si on a /deny ou /validate dans l'url, si la requête
    est en status created, si le user a right_review_export_jupyter
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
        (self.role_read_pseudo,
         self.role_read_nomi,
         self.role_exp_csv_pseudo,
         self.role_exp_csv_nomi,
         self.role_exp_jup_pseudo,
         self.role_exp_jup_nomi) = [
            Role.objects.create(**dict([(f, f == right) for f in self.all_rights]), name=name)
            for (name, right) in [("READ_PSEUDO", "right_read_patient_pseudonymized"),
                                  ("READ_NOMI", "right_read_patient_nominative"),
                                  ("EXP_CSV_PSEUDO", "right_export_csv_pseudonymized"),
                                  ("EXP_CSV_NOMI", "right_export_csv_nominative"),
                                  ("EXP_JUP_PSEUDO", "right_export_jupyter_pseudonymized"),
                                  ("EXP_JUP_NOMI", "right_export_jupyter_nominative")]]

        # USERS
        self.user_with_no_right, ph_with_no_right = new_user_and_profile(
            email=f"with_no_right{END_TEST_EMAIL}")

        self.user1, self.prof_1 = new_user_and_profile(email=f"us1{END_TEST_EMAIL}")
        self.user2, self.prof_2 = new_user_and_profile(email=f"us2{END_TEST_EMAIL}")
        self.user3, self.prof_3 = new_user_and_profile(email=f"us3{END_TEST_EMAIL}")

        # ACCESSES
        self.user1_csv_nomi_acc: Access = Access.objects.create(
            perimeter=self.aphp,
            profile=self.prof_1,
            role=self.role_exp_csv_nomi
        )

        self.user1_csv_pseudo_acc: Access = Access.objects.create(
            perimeter=self.aphp,
            profile=self.prof_1,
            role=self.role_exp_csv_pseudo
        )

        self.user1_nomi_acc: Access = Access.objects.create(
            perimeter=self.aphp,
            profile=self.prof_1,
            role=self.role_read_nomi
        )
        self.user1_exp_jup_nomi_acc: Access = Access.objects.create(
            perimeter=self.aphp,
            profile=self.prof_1,
            role=self.role_exp_jup_nomi
        )
        self.user1_exp_jup_pseudo_acc: Access = Access.objects.create(
            perimeter=self.aphp,
            profile=self.prof_1,
            role=self.role_exp_jup_pseudo
        )
        self.user2_exp_jup_nomi_acc: Access = Access.objects.create(
            perimeter=self.aphp,
            profile=self.prof_2,
            role=self.role_exp_jup_nomi
        )
        self.user3_exp_jup_pseudo_acc: Access = Access.objects.create(
            perimeter=self.aphp,
            profile=self.prof_3,
            role=self.role_exp_jup_pseudo
        )
        self.user2_nomi_acc: Access = Access.objects.create(
            perimeter=self.aphp,
            profile=self.prof_2,
            role=self.role_read_nomi
        )
        self.user2_exp_csv_nomi_acc: Access = Access.objects.create(
            perimeter=self.aphp,
            profile=self.prof_2,
            role=self.role_exp_csv_nomi
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

        # Exports new flow with new models - v1
        self.infra_provider_aphp = InfrastructureProvider.objects.create(name="APHP")
        self.datalab = Datalab.objects.create(name="main_datalab", infrastructure_provider=self.infra_provider_aphp)
        self.user1_export = Export.objects.create(output_format=ExportType.HIVE,
                                                  owner=self.user1,
                                                  status=ExportStatus.PENDING.name,
                                                  target_name="12345_09092023_151500",
                                                  datalab=self.datalab)
        ExportTable.objects.create(export=self.user1_export,
                                   name="person",
                                   cohort_result_source=self.user1_cohort,
                                   cohort_result_subset=self.user1_cohort)
        ExportTable.objects.create(export=self.user1_export,
                                   name="other_table",
                                   cohort_result_source=self.user1_cohort,
                                   cohort_result_subset=self.user1_cohort)


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

    def test_list_requests_as_user1(self):
        base_results = self.user1_reqs

        self.check_get_paged_list_case(ListCase(to_find=base_results,
                                                page_size=20,
                                                user=self.user1,
                                                status=status.HTTP_200_OK,
                                                success=True,
                                                params={"owner": self.user1.pk}))


class DownloadCase(RequestCase):
    def __init__(self, export: ExportRequest, mock_hdfs_resp: Any = None,
                 mock_file_size_resp: Any = None, mock_hdfs_called: bool = True,
                 mock_file_size_called: bool = True, **kwargs):
        self.export = export
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
            export=self.model_objects.create(**self.base_data),
            success=True,
            status=status.HTTP_200_OK,
        )
        self.base_err_download_case = self.base_download_case.clone(
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
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

    # disabled for now as the reviewing workflow is not established.
    # for now, users can only retrieve their own export requests
    # def test_get_request_as_csv_reviewer(self):
    #     # As a Csv export reviewer, I can retrieve a CSV ExportRequest
    #     # from another user
    #     self.check_retrieve_case(RetrieveCase(
    #         to_find=self.user2_exp_req_succ,
    #         view_params=dict(id=self.user2_exp_req_succ.id),
    #         status=status.HTTP_200_OK,
    #         user=self.user_csv_reviewer,
    #         success=True,
    #     ))

    def test_error_get_request_not_owner(self):
        # As a simple user, I cannot retrieve another user's ExportRequest
        self.check_retrieve_case(RetrieveCase(
            to_find=self.user2_exp_req_succ,
            view_params=dict(id=self.user2_exp_req_succ.id),
            status=status.HTTP_403_FORBIDDEN,
            user=self.user1,
            success=False,
        ))

    @mock.patch('exports.conf_exports.stream_gen')
    @mock.patch('exports.conf_exports.get_file_size')
    def check_download(self, case: DownloadCase, mock_get_file_size: MagicMock, mock_hdfs_stream_gen: MagicMock):
        mock_hdfs_stream_gen.return_value = case.mock_hdfs_resp
        mock_get_file_size.return_value = case.mock_file_size_resp

        export = case.export

        request = self.factory.get(self.objects_url)

        if case.user:
            force_authenticate(request, case.user)
        response = self.__class__.download_view(request, id=export.pk)
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
                f"{export.cohort_id}.zip"
            )
            self.assertEquals(response.get('Content-length'), '1')
        else:
            self.assertNotEqual(
                response.get('Content-Disposition'),
                f"attachment; filename=export_"
                f"{export.cohort_id}.zip"
            )
            self.assertNotEqual(response.get('Content-length'), '1')

        mock_hdfs_stream_gen.assert_called_once() if case.mock_hdfs_called \
            else mock_hdfs_stream_gen.assert_not_called()
        mock_get_file_size.assert_called_once() if case.mock_file_size_called \
            else mock_get_file_size.assert_not_called()

    def test_download_request_result(self):
        # As a user, I can download the result of an ExportRequest I created
        self.check_download(self.base_download_case)

    def test_error_download_old_request(self):
        # As a user, I cannot download the result of
        # an ExportRequest that is too old and its outcome has been removed from HDFS
        old_export = self.model_objects.create(**self.base_data)
        old_export.insert_datetime = timezone.now() - timedelta(days=30)
        old_export.save()
        self.check_download(self.base_err_download_case.clone(export=old_export,
                                                              status=status.HTTP_204_NO_CONTENT))

    def test_error_download_request_not_finished(self):
        # As a user, I cannot download the result of
        # an ExportRequest that is not finished
        export = self.base_err_download_case.export
        export.request_job_status = JobStatus.pending
        export.save()
        self.check_download(self.base_err_download_case)

    def test_error_download_request_not_csv(self):
        # As a user, I cannot download the result of an ExportRequest that is
        # not of type CSV and with job status finished
        export = self.base_err_download_case.export
        export.output_format = ExportType.HIVE
        export.save()
        self.check_download(self.base_err_download_case.clone(status=status.HTTP_400_BAD_REQUEST))

    def test_error_download_request_result_not_owned(self):
        # As a user, I can download the result of another user's ExportRequest
        export = self.base_err_download_case.export
        export.owner = self.user2
        export.save()
        self.check_download(self.base_err_download_case.clone(status=status.HTTP_403_FORBIDDEN))

# JOBS ##################################################################


class ExportsJobsTests(ExportsWithSimpleSetUp):

    @mock.patch('exports.tasks.push_email_notification')
    @mock.patch('exports.conf_exports.delete_file')
    def test_task_delete_export_requests_csv_files(self, mock_delete_hdfs_file, mock_push_email_notif):
        from admin_cohort.settings import DAYS_TO_DELETE_CSV_FILES
        mock_delete_hdfs_file.return_value = None
        mock_push_email_notif.return_value = None
        self.user1_exp_req_succ.insert_datetime = (timezone.now() - timedelta(days=DAYS_TO_DELETE_CSV_FILES))
        self.user1_exp_req_succ.is_user_notified = True
        self.user1_exp_req_succ.save()
        delete_export_requests_csv_files()
        deleted_ers = list(ExportRequest.objects.filter(cleaned_at__isnull=False))
        self.assertCountEqual([er.pk for er in deleted_ers], [self.user1_exp_req_succ.pk])
        [self.assertAlmostEqual((er.cleaned_at - timezone.now()).total_seconds(), 0, delta=1) for er in deleted_ers]

    @mock.patch('exports.tasks.push_email_notification')
    @mock.patch('exports.conf_exports.prepare_hive_db')
    @mock.patch('exports.conf_exports.post_export')
    @mock.patch('exports.conf_exports.conclude_export_hive')
    @mock.patch('exports.conf_exports.get_job_status')
    def test_task_launch_request(self, mock_get_job_status, mock_prepare_hive_db, mock_post_export, mock_conclude_export_hive,
                                 mock_push_email_notification):
        mock_get_job_status.return_value = JobStatusResponse(job_status=ApiJobStatus.FinishedSuccessfully.value)
        mock_prepare_hive_db.return_value = None
        mock_post_export.return_value = None
        mock_conclude_export_hive.return_value = None
        mock_push_email_notification.return_value = None
        launch_request(er_id=self.user1_exp_req_succ.id)
        mock_get_job_status.assert_called()
        mock_prepare_hive_db.assert_not_called()
        mock_post_export.assert_called()
        mock_conclude_export_hive.assert_not_called()
        mock_push_email_notification.assert_called()

    @mock.patch.object(requests, 'post')
    @mock.patch('exports.tasks.push_email_notification')
    @mock.patch('exports.conf_exports.prepare_hive_db')
    @mock.patch('exports.conf_exports.conclude_export_hive')
    @mock.patch('exports.conf_exports.get_job_status')
    def test_task_launch_export_task_jupyter(self, mock_get_job_status, mock_prepare_hive_db, mock_conclude_export_hive,
                                             mock_push_email_notification, mock_post):
        mock_get_job_status.return_value = JobStatusResponse(job_status=ApiJobStatus.FinishedSuccessfully.value)
        mock_prepare_hive_db.return_value = None
        mock_conclude_export_hive.return_value = None
        mock_push_email_notification.return_value = None
        mock_response = Response()
        mock_response.status_code = status.HTTP_201_CREATED
        mock_response._text = 'returned some task_id'
        mock_response._content = b'{"task_id": "some-task-uuid"}'
        mock_post.return_value = mock_response
        launch_export_task(export_id=self.user1_export.uuid)
        mock_get_job_status.assert_called()
        mock_prepare_hive_db.assert_called()
        mock_conclude_export_hive.assert_called()
        mock_push_email_notification.assert_called()

    @mock.patch('exports.conf_exports.mark_export_request_as_failed')
    @mock.patch('exports.conf_exports.prepare_hive_db')
    def test_task_launch_export_task_jupyter_failure_1(self, mock_prepare_hive_db, mock_mark_export_request_as_failed):
        mock_prepare_hive_db.side_effect = RequestException()
        mock_mark_export_request_as_failed.return_value = None
        launch_export_task(export_id=self.user1_export.uuid)
        mock_prepare_hive_db.assert_called()
        mock_mark_export_request_as_failed.assert_called()

    @mock.patch('exports.conf_exports.mark_export_request_as_failed')
    @mock.patch('exports.conf_exports.post_export_v1')
    @mock.patch('exports.conf_exports.prepare_hive_db')
    def test_task_launch_export_task_jupyter_failure_2(self, mock_prepare_hive_db, mock_post_export_v1, mock_mark_export_request_as_failed):
        mock_prepare_hive_db.return_value = None
        mock_post_export_v1.side_effect = RequestException()
        mock_mark_export_request_as_failed.return_value = None
        launch_export_task(export_id=self.user1_export.uuid)
        mock_post_export_v1.assert_called()
        mock_prepare_hive_db.assert_called()
        mock_mark_export_request_as_failed.assert_called()

    @mock.patch('exports.conf_exports.mark_export_request_as_failed')
    @mock.patch('exports.conf_exports.wait_for_export_job')
    @mock.patch('exports.conf_exports.post_export_v1')
    @mock.patch('exports.conf_exports.prepare_hive_db')
    def test_task_launch_export_task_jupyter_failure_3(self, mock_prepare_hive_db, mock_post_export_v1, mock_wait_for_export_job,
                                                       mock_mark_export_request_as_failed):
        mock_prepare_hive_db.return_value = None
        mock_post_export_v1.return_value = None
        mock_wait_for_export_job.side_effect = HTTPError()
        mock_mark_export_request_as_failed.return_value = None
        launch_export_task(export_id=self.user1_export.uuid)
        mock_prepare_hive_db.assert_called()
        mock_post_export_v1.assert_called()
        mock_wait_for_export_job.assert_called()
        mock_mark_export_request_as_failed.assert_called()

    @mock.patch('exports.conf_exports.mark_export_request_as_failed')
    @mock.patch('exports.conf_exports.conclude_export_hive')
    @mock.patch('exports.conf_exports.wait_for_export_job')
    @mock.patch('exports.conf_exports.post_export_v1')
    @mock.patch('exports.conf_exports.prepare_hive_db')
    def test_task_launch_export_task_jupyter_failure_4(self, mock_prepare_hive_db, mock_post_export_v1, mock_wait_for_export_job,
                                                       mock_conclude_export_hive, mock_mark_export_request_as_failed):
        mock_prepare_hive_db.return_value = None
        mock_post_export_v1.return_value = None
        mock_wait_for_export_job.return_value = None
        mock_conclude_export_hive.side_effect = RequestException()
        mock_mark_export_request_as_failed.return_value = None
        launch_export_task(export_id=self.user1_export.uuid)
        mock_prepare_hive_db.assert_called()
        mock_post_export_v1.assert_called()
        mock_wait_for_export_job.assert_called()
        mock_conclude_export_hive.assert_called()
        mock_mark_export_request_as_failed.assert_called()

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
    @mock.patch('exports.views.export_request.push_email_notification')
    @mock.patch('exports.emails.EMAIL_REGEX_CHECK', REGEX_TEST_EMAIL)
    def check_create_case(self, case: ExportCreateCase, mock_push_email_notif: MagicMock, mock_task: MagicMock):
        mock_task.return_value = None
        mock_push_email_notif.return_value = None
        super(ExportsCreateTests, self).check_create_case(case)
        mock_task.assert_called() if case.success else mock_task.assert_not_called()
        mock_push_email_notif.assert_called() if case.success else mock_push_email_notif.assert_not_called()


class ExportsCsvCreateTests(ExportsCreateTests):
    def setUp(self):
        super(ExportsCsvCreateTests, self).setUp()

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

    def test_error_create_export_with_not_owned_cohort(self):
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
        # I cannot create a CSV export request with pseudo mode
        case = self.err_basic_case.clone(
            data={**self.basic_data, 'nominative': False},
            created=False,
            status=status.HTTP_400_BAD_REQUEST,
        )
        self.check_create_case(case)


class ExportsJupyterCreateTests(ExportsCreateTests):
    def setUp(self):
        super(ExportsJupyterCreateTests, self).setUp()

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
    def check_create_case(self, case: ExportJupyterCreateCase, mock_user_bound: MagicMock):
        mock_user_bound.return_value = case.mock_user_bound_resp
        super(ExportsJupyterCreateTests, self).check_create_case(case)
        mock_user_bound.assert_called() if case.mock_user_bound_called else mock_user_bound.assert_not_called()

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

        self.user1_exp_jup_nomi_acc.end_datetime = timezone.now() - timedelta(days=2)
        self.user1_exp_jup_nomi_acc.save()

        self.check_create_case(self.err_basic_case.clone(
            created=False,
            status=status.HTTP_403_FORBIDDEN,
            mock_user_bound_called=False,
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
        mock_get_job_status.return_value = JobStatusResponse(job_status=ApiJobStatus.FinishedSuccessfully.value)
        result = wait_for_hive_db_creation_job(job_id="random_task_id")
        self.assertIsNone(result)

    @mock.patch("exports.conf_exports.get_job_status")
    @mock.patch("exports.conf_exports.time.sleep")
    def test_failure_on_wait_for_hive_db_creation_job(self, mock_sleep, mock_get_job_status):
        mock_sleep.return_value = None
        mock_get_job_status.return_value = JobStatusResponse(job_status=ApiJobStatus.Failure.value)
        with self.assertRaises(HTTPError):
            wait_for_hive_db_creation_job(job_id="random_task_id")

    @mock.patch("exports.conf_exports.requests.get")
    def test_get_job_status(self, mock_requests_get):
        resp = Response()
        resp.status_code = 200
        resp._content = b'{"task_status": "Pending", "stdout": "", "stderr": ""}'
        mock_requests_get.return_value = resp
        status_response = get_job_status(service="hadoop", job_id="random_task_id")
        self.assertEqual(status_response.job_status, JobStatus.pending.value)
        self.assertEqual(status_response.out, "")
        self.assertEqual(status_response.err, "")

    @mock.patch("exports.conf_exports.requests.get")
    def test_get_job_status_with_unknown_status(self, mock_requests_get):
        resp = Response()
        resp.status_code = 200
        resp._content = b'{"task_status": "WRONG", "stdout": "output", "stderr": "error"}'
        mock_requests_get.return_value = resp
        status_response = get_job_status(service="hadoop", job_id="random_task_id")
        self.assertEqual(status_response.job_status, JobStatus.unknown.value)
        self.assertEqual(status_response.out, "output")
        self.assertEqual(status_response.err, "error")

    @mock.patch("exports.conf_exports.requests.get")
    def test_get_job_status_with_bad_status_code(self, mock_requests_get):
        resp = Response()
        resp.status_code = 403
        mock_requests_get.return_value = resp
        with self.assertRaises(HTTPError):
            _ = get_job_status(service="hadoop", job_id="random_task_id")

    @mock.patch("exports.conf_exports.get_job_status")
    @mock.patch("exports.conf_exports.time.sleep")
    def test_wait_for_export_job(self, mock_sleep, mock_get_job_status):
        mock_sleep.return_value = None
        mock_get_job_status.return_value = JobStatusResponse(job_status=ApiJobStatus.FinishedSuccessfully.value)
        wait_for_export_job(er=self.export_request)
        self.assertEqual(self.export_request.request_job_status, JobStatus.finished.value)

    @mock.patch("exports.conf_exports.log_export_request_task")
    @mock.patch("exports.conf_exports.get_job_status")
    @mock.patch("exports.conf_exports.time.sleep")
    def test_wait_for_export_job_error(self, mock_sleep, mock_get_job_status, mock_log_request_task):
        mock_sleep.return_value = None
        mock_get_job_status.side_effect = RequestException()
        mock_log_request_task.return_value = None
        with self.assertRaises(HTTPError):
            wait_for_export_job(er=self.export_request)
        mock_log_request_task.assert_called()

    @mock.patch("exports.conf_exports.push_email_notification")
    def test_mark_export_request_as_failed(self, mock_push_email_notification):
        mock_push_email_notification.return_value = None
        mark_export_request_as_failed(er=self.export_request,
                                      e=Exception("Error while processing export"),
                                      msg="Error message",
                                      start=timezone.now())
        mock_push_email_notification.assert_called()
        self.assertEqual(self.export_request.request_job_status, JobStatus.failed.value)
        self.assertIsNotNone(self.export_request.request_job_duration)
        self.assertTrue(self.export_request.is_user_notified)


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
