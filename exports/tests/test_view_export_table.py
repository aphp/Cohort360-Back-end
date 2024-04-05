from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from admin_cohort.tests.tests_tools import new_user_and_profile
from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from exports.models import ExportTable, Export, Datalab
from exports.services.export import export_service
from exports.tests.base_test import ExportsTestBase
from exports.enums import ExportStatus, ExportType
from exports.views import ExportTableViewSet


class ExportTableViewSetTest(ExportsTestBase):
    view_set = ExportTableViewSet
    view_root = "exports:v1:export_tables"
    model = ExportTable

    def setUp(self):
        super().setUp()
        self.datalab = Datalab.objects.create(infrastructure_provider=self.infra_provider_aphp)
        self.export = Export.objects.create(output_format=ExportType.CSV,
                                            owner=self.datalabs_manager_user,
                                            datalab=self.datalab,
                                            status=ExportStatus.PENDING,
                                            target_name="12345_09092023_151500")
        self.export_tables = [ExportTable.objects.create(name=f"export_table_{i}",
                                                         export=self.export) for i in range(5)]
        self.target_export_table_to_retrieve = self.export_tables[0]

    def test_list_export_tables(self):
        list_url = reverse(viewname=self.viewname_list)
        self.check_test_list_view(list_url=list_url,
                                  request_user=self.csv_exporter_user,
                                  expected_resp_status=status.HTTP_200_OK,
                                  result_count=len(self.export_tables)-1)

    def test_retrieve_export_table(self):
        retrieve_url = reverse(viewname=self.viewname_detail, args=[self.target_export_table_to_retrieve.uuid])
        self.check_test_retrieve_view(request_user=self.csv_exporter_user,
                                      retrieve_url=retrieve_url,
                                      obj_id=self.target_export_table_to_retrieve.uuid,
                                      expected_resp_status=status.HTTP_200_OK,
                                      to_read_from_response='name',
                                      to_check_against=self.target_export_table_to_retrieve.name)


class ExportTableServiceTests(TestCase):

    def setUp(self) -> None:
        self.exporter_user, _ = new_user_and_profile(email="usr.exporter@aphp.fr")
        self.person_table_name = "person"
        self.cohorts = [CohortResult.objects.create(name=f"Cohort {i}",
                                                    owner=self.exporter_user,
                                                    request_job_status=JobStatus.finished) for i in range(3)]

    def test_validate_tables_data_all_tables_have_source_cohort(self):
        # all tables have a linked source cohort
        tables_data = [{"name": self.person_table_name, "cohort_result_source": self.cohorts[0].uuid},
                       {"name": "other_table_01", "cohort_result_source": self.cohorts[1].uuid},
                       {"name": "other_table_02", "cohort_result_source": self.cohorts[2].uuid}]
        check = export_service.validate_tables_data(tables_data=tables_data)
        self.assertTrue(check)

    def test_validate_tables_data_only_person_table_has_source_cohort(self):
        # only `person` table has a linked source cohort, the other tables don't
        tables_data = [{"name": self.person_table_name, "cohort_result_source": self.cohorts[0].uuid},
                       {"name": "table_01"},
                       {"name": "table_02"}]
        check = export_service.validate_tables_data(tables_data=tables_data)
        self.assertTrue(check)

    def test_validate_tables_data_one_table_with_source_cohort(self):
        # tables data is valid if the source cohort is provided within the table data
        tables_data = [{"name": "table_01", "cohort_result_source": self.cohorts[0].uuid}]
        check = export_service.validate_tables_data(tables_data=tables_data)
        self.assertTrue(check)

    def test_validate_tables_data_missing_source_cohort_for_person_table(self):
        # tables tada is not valid if the `person` table dict is in the list but missing the source cohort
        tables_data = [{"name": self.person_table_name},
                       {"name": "table_01", "cohort_result_source": self.cohorts[0].uuid}]
        with self.assertRaises(ValueError):
            export_service.validate_tables_data(tables_data=tables_data)

    def test_validate_tables_data_with_only_person_table_without_source_cohort(self):
        # tables data is not valid if the `person` table has no source cohort
        tables_data = [{"name": self.person_table_name}]
        with self.assertRaises(ValueError):
            export_service.validate_tables_data(tables_data=tables_data)

    def test_validate_tables_data_all_tables_without_source_cohort(self):
        # tables data is not valid if the `person` table has no source cohort
        tables_data = [{"name": "table_01"},
                       {"name": "table_02"}]
        with self.assertRaises(ValueError):
            export_service.validate_tables_data(tables_data=tables_data)
