from datetime import timedelta

from django.utils import timezone

from accesses.models import Access, Perimeter, Role
from admin_cohort.tests.tests_tools import new_user_and_profile, TestCaseWithDBs
from admin_cohort.types import JobStatus
from cohort.models import CohortResult, Folder, Request, RequestQuerySnapshot
from exporters.enums import ExportTypes
from exports.models import Export, Datalab, InfrastructureProvider, ExportTable


class ExportersTestBase(TestCaseWithDBs):

    def setUp(self):
        self.csv_exporter_user, self.csv_exporter_profile = new_user_and_profile()
        self.hive_user, self.hive_profile = new_user_and_profile()
        self.second_csv_exporter_user, self.second_csv_exporter_profile = new_user_and_profile()
        self.perimeter_aphp = Perimeter.objects.create(name="APHP", local_id="1", cohort_id="1")
        self.csv_exporter_role = Role.objects.create(name="CSV EXPORTER", right_export_csv_xlsx_nominative=True)
        self.csv_exporter_access = Access.objects.create(profile=self.csv_exporter_profile,
                                                         perimeter=self.perimeter_aphp,
                                                         role=self.csv_exporter_role,
                                                         start_datetime=timezone.now(),
                                                         end_datetime=timezone.now() + timedelta(days=365))
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
                                                  group_id="11111")
        self.cohort2 = CohortResult.objects.create(name="Second Cohort",
                                                   owner=self.csv_exporter_user,
                                                   request_query_snapshot=self.rqs,
                                                   request_job_status=JobStatus.finished,
                                                   group_id="22222")
        self.cohort3 = CohortResult.objects.create(name="Third Cohort",
                                                   owner=self.second_csv_exporter_user,
                                                   request_query_snapshot=self.rqs,
                                                   request_job_status=JobStatus.finished,
                                                   group_id="33333")
        self.infrastructure_provider = InfrastructureProvider.objects.create(name="Main")
        self.datalab = Datalab.objects.create(name='user1', infrastructure_provider=self.infrastructure_provider)

        export_vals = dict(owner=self.csv_exporter_user,
                           target_location="target_location",
                           target_name="target_name",
                           nominative=True
                           )
        self.csv_export = Export.objects.create(**export_vals, output_format=ExportTypes.CSV.value)
        self.csv_export_table = ExportTable.objects.create(export=self.csv_export,
                                                           name="person",
                                                           cohort_result_source=self.cohort,
                                                           columns=["person_id", "person_name"])
        self.csv_export_table_with_options = ExportTable.objects.create(export=self.csv_export,
                                                                        name="special_table",
                                                                        cohort_result_source=self.cohort,
                                                                        columns=["col_01", "col_02"],
                                                                        pivot_merge_columns=["col_03", "col_04"],
                                                                        pivot_merge_ids=["col_03", "col_04"])
        self.xlsx_export = Export.objects.create(**export_vals, output_format=ExportTypes.XLSX.value, group_tables=True)
        self.xlsx_export_table = ExportTable.objects.create(export=self.xlsx_export,
                                                            name="person",
                                                            cohort_result_source=self.cohort)
        self.hive_export = Export.objects.create(**export_vals,
                                                 output_format=ExportTypes.HIVE.value,
                                                 datalab=self.datalab)
        self.hive_export_table = ExportTable.objects.create(export=self.hive_export,
                                                            name="person",
                                                            cohort_result_source=self.cohort)
