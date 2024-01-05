from unittest import TestCase

from django.urls import reverse
from rest_framework import status

from exports.models import ExportTable, Export, Datalab
from exports.services.export import export_service
from exports.tests.base_test import ExportsTestBase
from exports.types import ExportType, ExportStatus
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
        super().setUp()
        self.person_table_name = "person"

    def test_validate_tables_data_success_all_tables_have_source_cohort(self):
        # all tables have a linked source cohort
        tables_data = [{"name": self.person_table_name, "cohort_result_source": "cohort_for_person"},
                       {"name": "other_table_01", "cohort_result_source": "cohort_01"},
                       {"name": "other_table_02", "cohort_result_source": "cohort_02"}]
        check = export_service.validate_tables_data(tables_data=tables_data)
        self.assertTrue(check)

    def test_validate_tables_data_success_only_person_table_has_source_cohort(self):
        # only `person` table has a linked source cohort, the other tables don't
        tables_data = [{"name": self.person_table_name, "cohort_result_source": "cohort_for_person"},
                       {"name": "table_01", "cohort_result_source": None},
                       {"name": "table_02", "cohort_result_source": None}]
        check = export_service.validate_tables_data(tables_data=tables_data)
        self.assertTrue(check)

    def test_validate_tables_data_success_some_table_with_source_cohort(self):
        # tables data is valid if the source cohort is provided within the table data
        tables_data = [{"name": "table_01",
                        "cohort_result_source": "cohort_01"}]
        check = export_service.validate_tables_data(tables_data=tables_data)
        self.assertTrue(check)

    def test_validate_tables_data_error_missing_source_cohort_for_person_table(self):
        # tables tada is not valid if the `person` table dict is in the list but missing the source cohort
        tables_data = [{"name": self.person_table_name, "cohort_result_source": None},
                       {"name": "table_01", "cohort_result_source": "cohort_01"}]
        with self.assertRaises(ValueError):
            export_service.validate_tables_data(tables_data=tables_data)

    def test_validate_tables_data_error_with_only_person_table_without_source_cohort(self):
        # tables data is not valid if the `person` table has no source cohort
        tables_data = [{"name": self.person_table_name,
                        "cohort_result_source": None}]
        with self.assertRaises(ValueError):
            export_service.validate_tables_data(tables_data=tables_data)

    def test_validate_tables_data_error_all_tables_without_source_cohort(self):
        # tables data is not valid if the `person` table has no source cohort
        tables_data = [{"name": "table_01", "cohort_result_source": None},
                       {"name": "table_02", "cohort_result_source": None}]
        with self.assertRaises(ValueError):
            export_service.validate_tables_data(tables_data=tables_data)
