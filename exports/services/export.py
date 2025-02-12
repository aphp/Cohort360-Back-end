import logging
from typing import List
from urllib.parse import quote_plus

from django.http import StreamingHttpResponse
from rest_framework.exceptions import ValidationError

from admin_cohort.types import JobStatus
from cohort.models import CohortResult, FhirFilter
from cohort.services.cohort_result import cohort_service
from exports.models import ExportTable, Export
from exports.services.export_operators import ExportDownloader, ExportManager
from exports.tasks import launch_export_task

_logger = logging.getLogger('info')


def get_encoded_doc_ref_filter() -> str:
    filter_values = {"type:not": "https://terminology.eds.aphp.fr/aphp-orbis-document-textuel-hospitalier|doc-impor",
                     "contenttype": "text/plain"
                     }
    return "&".join([f"{key}={quote_plus(val)}" for key, val in filter_values.items()])


EXCLUDED_TABLES = ('imaging_series',
                   'questionnaire__item',
                   'questionnaireresponse__item',
                   'questionnaireresponse__item__answer')

TABLES_REQUIRING_SUB_COHORTS = ('note',)

RESOURCE_FILTERS = {TABLES_REQUIRING_SUB_COHORTS[0]: ("DocumentReference", get_encoded_doc_ref_filter())
                    }


class ExportService:

    @staticmethod
    def validate_export_data(data: dict, **kwargs) -> None:
        try:
            ExportManager().validate(export_data=data, **kwargs)
        except Exception as e:
            raise ValidationError(f'Invalid export data: {e}')

    def proceed_with_export(self, export: Export, tables: List[dict], **kwargs) -> None:
        requires_cohort_subsets = self.create_tables(export, tables, **kwargs)
        if not requires_cohort_subsets:
            launch_export_task.delay(export.pk)

    @staticmethod
    def force_generate_fhir_filter(export: Export, table_name: str) -> str:
        resource, _filter = RESOURCE_FILTERS[table_name]
        return FhirFilter.objects.create(auto_generated=True,
                                         fhir_resource=resource,
                                         filter=_filter,
                                         name=f'{str(export.uuid)[:8]}_{table_name}_(auto generated)',
                                         owner=export.owner).uuid

    def create_tables(self, export: Export, tables: List[dict], **kwargs) -> bool:
        requires_cohort_subsets = False
        for table in tables:
            fhir_filter_id = table.get("fhir_filter")
            cohort_source_id = table.get("cohort_result_source")
            cohort_source = cohort_source_id and CohortResult.objects.get(pk=cohort_source_id) or None
            table_name = table.get("table_name")
            if fhir_filter_id and cohort_source is None:
                raise ValidationError("A FHIR filter was provided but not a cohort source to filter")
            if cohort_source and table_name in TABLES_REQUIRING_SUB_COHORTS and not fhir_filter_id:
                fhir_filter_id = self.force_generate_fhir_filter(export=export,
                                                                 table_name=table_name)

            if cohort_source and fhir_filter_id and table_name not in EXCLUDED_TABLES:
                requires_cohort_subsets = True
                cohort_subset = cohort_service.create_cohort_subset(request=kwargs.get("http_request"),
                                                                    owner_id=export.owner_id,
                                                                    table_name=table_name,
                                                                    fhir_filter_id=fhir_filter_id,
                                                                    source_cohort=cohort_source)
            else:
                cohort_subset = None

            ExportTable.objects.create(export=export,
                                       name=table_name,
                                       fhir_filter_id=fhir_filter_id,
                                       cohort_result_source=cohort_source,
                                       cohort_result_subset=cohort_subset,
                                       columns=table.get("columns"),
                                       pivot=bool(table.get("pivot")),
                                       pivot_split=bool(table.get("pivot_split")),
                                       pivot_merge=bool(table.get("pivot_merge")))
        return requires_cohort_subsets

    @staticmethod
    def check_all_cohort_subsets_created(export: Export):
        _logger.info(f"Export[{export.uuid}]: Checking if all cohort subsets were created...")
        for table in export.export_tables.filter(cohort_result_subset__isnull=False):
            cohort_subset_status = table.cohort_result_subset.request_job_status
            if cohort_subset_status == JobStatus.failed.value:
                failure_reason = "One or multiple cohort subsets has failed"
                _logger.info(f"Export[{export.uuid}]: Aborting export - {failure_reason}")
                ExportManager().mark_as_failed(export=export, reason=failure_reason)
                return
            elif cohort_subset_status != JobStatus.finished.value:
                _logger.info(f"Export[{export.uuid}]: waiting for cohort subsets to finish before launching export")
                return
        _logger.info(f"Export[{export.uuid}]: all cohort subsets were successfully created. Launching export.")
        launch_export_task.delay(export.pk)

    @staticmethod
    def download(export: Export) -> StreamingHttpResponse:
        return ExportDownloader().download(export=export)


export_service = ExportService()
