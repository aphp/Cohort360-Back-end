from django.test import TestCase

from accesses.models import Access, Perimeter, Role
from admin_cohort.tests.tests_tools import new_user_and_profile
from admin_cohort.types import JobStatus
from cohort.models import CohortResult, Folder, Request, RequestQuerySnapshot
from exporters.enums import ExportTypes
from exports.models import ExportRequest
from workspaces.models import Account


class ExportersTestBase(TestCase):

    def setUp(self):
        self.csv_exporter_user, self.csv_exporter_profile = new_user_and_profile(email="csv.exporter@aphp.fr")
        self.hive_exporter_user, self.hive_exporter_profile = new_user_and_profile(email="hive.exporter@aphp.fr")
        self.second_csv_exporter_user, self.second_csv_exporter_profile = new_user_and_profile(email="csv.exporter.2nd@aphp.fr")
        self.perimeter_aphp = Perimeter.objects.create(name="APHP", local_id="1", cohort_id="1")
        self.csv_exporter_role = Role.objects.create(name="CSV EXPORTER", right_export_csv_nominative=True)
        self.csv_exporter_access = Access.objects.create(profile=self.csv_exporter_profile,
                                                         perimeter=self.perimeter_aphp,
                                                         role=self.csv_exporter_role)
        self.folder = Folder.objects.create(name="TestFolder", owner=self.csv_exporter_user)
        self.request = Request.objects.create(name="TestRequest", owner=self.csv_exporter_user, parent_folder=self.folder)
        self.rqs = RequestQuerySnapshot.objects.create(owner=self.csv_exporter_user,
                                                       request=self.request,
                                                       serialized_query="{}",
                                                       perimeters_ids=[self.perimeter_aphp.cohort_id])
        self.cohort = CohortResult.objects.create(name="Cohort For Export Purposes",
                                                  owner=self.csv_exporter_user,
                                                  request_query_snapshot=self.rqs,
                                                  request_job_status=JobStatus.finished,
                                                  fhir_group_id="11111")
        self.cohort2 = CohortResult.objects.create(name="Second Cohort",
                                                   owner=self.csv_exporter_user,
                                                   request_query_snapshot=self.rqs,
                                                   request_job_status=JobStatus.finished,
                                                   fhir_group_id="22222")
        self.cohort3 = CohortResult.objects.create(name="Third Cohort",
                                                   owner=self.second_csv_exporter_user,
                                                   request_query_snapshot=self.rqs,
                                                   request_job_status=JobStatus.finished,
                                                   fhir_group_id="33333")
        self.unix_account = Account.objects.create(username='user1', spark_port_start=0)

        export_vals = dict(owner=self.csv_exporter_user,
                           cohort_fk=self.cohort,
                           cohort_id=self.cohort.fhir_group_id,
                           target_location="target_location",
                           target_name="target_name",
                           nominative=True
                           )
        self.csv_export = ExportRequest.objects.create(**export_vals, output_format=ExportTypes.CSV.value)
        self.hive_export = ExportRequest.objects.create(**export_vals,
                                                        output_format=ExportTypes.HIVE.value,
                                                        target_unix_account=self.unix_account)