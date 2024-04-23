import random
from typing import List
from rest_framework import status

from accesses.models import Access, Role, Perimeter
from admin_cohort.types import JobStatus
from admin_cohort.models import User
from admin_cohort.tests.tests_tools import new_user_and_profile, ViewSetTestsWithBasicPerims, random_str, ListCase, \
    RetrieveCase, PatchCase, DeleteCase
from cohort.models import CohortResult, RequestQuerySnapshot, Request, DatedMeasure, Folder
from workspaces.models import Account
from exports import ExportTypes
from exports.models import ExportRequest, ExportRequestTable, Export, ExportTable, InfrastructureProvider, Datalab
from exports.enums import ExportStatus
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
        self.export_type = ExportTypes.default()

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
                output_format=self.export_type,
                provider_id=self.user1.provider_id,
                request_job_status=JobStatus.finished,
                target_location="user1_exp_req_succ",
                is_user_notified=False,
                nominative=True
            )
        self.user1_exp_req_succ_table1: ExportRequestTable = \
            ExportRequestTable.objects.create(
                export_request=self.user1_exp_req_succ,
                omop_table_name="table_x",
            )

        self.user1_exp_req_fail: ExportRequest = \
            ExportRequest.objects.create(
                owner=self.user1,
                cohort_fk=self.user1_cohort,
                cohort_id=42,
                output_format=self.export_type,
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
                output_format=self.export_type,
                provider_id=self.user1.provider_id,
                request_job_status=JobStatus.finished.value,
                target_location="user2_exp_req_succ",
                is_user_notified=True,
            )

        # Exports new flow with new models - v1
        self.infra_provider_aphp = InfrastructureProvider.objects.create(name="APHP")
        self.datalab = Datalab.objects.create(name="main_datalab", infrastructure_provider=self.infra_provider_aphp)
        self.user1_export = Export.objects.create(output_format=self.export_type,
                                                  owner=self.user1,
                                                  status=ExportStatus.PENDING.value,
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
                output_format=random.choice([self.export_type,
                                             self.export_type]),
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
                    output_format=random.choice([self.export_type,
                                                 self.export_type]),
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


class ExportsRetrieveTests(ExportsWithSimpleSetUp):
    download_view = ExportRequestViewSet.as_view({'get': 'download'})

    def setUp(self):
        super(ExportsRetrieveTests, self).setUp()
        self.base_data = dict(
            owner=self.user1,
            cohort_fk=self.user1_cohort,
            cohort_id=42,
            output_format=self.export_type,
            provider_id=self.user1.provider_id,
            request_job_status=JobStatus.finished.value,
            target_location="location_example",
            is_user_notified=False,
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
            output_format=self.export_type,
            provider_id=self.user1.provider_id,
            request_job_status=JobStatus.new.value,
            target_location="user1_exp_req_succ",
            is_user_notified=False,

        )
        self.basic_csv_data = {**self.basic_jup_data,
                               'output_format': self.export_type}


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
