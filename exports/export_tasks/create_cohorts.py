import logging
from typing import List, Dict
from urllib.parse import quote_plus

from celery import shared_task

from cohort.models import CohortResult, FhirFilter
from cohort.services.cohort_result import cohort_service
from cohort.services.utils import ServerError
from exports.tools import get_export_by_id
from exports.models import Export


TABLES_REQUIRING_SUB_COHORTS = ('note',)
EXCLUDED_TABLES = ('imaging_series',
                   'questionnaire__item',
                   'questionnaireresponse__item',
                   'questionnaireresponse__item__answer'
                   )

_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')


def get_encoded_doc_ref_filter() -> str:
    filter_values = {"type:not": "https://terminology.eds.aphp.fr/aphp-orbis-document-textuel-hospitalier|doc-impor",
                     "contenttype": "text/plain"
                     }
    return "&".join([f"{key}={quote_plus(val)}" for key, val in filter_values.items()])


RESOURCE_FILTERS = {TABLES_REQUIRING_SUB_COHORTS[0]: ("DocumentReference", get_encoded_doc_ref_filter())}


def force_generate_fhir_filter(export: Export, table_name: str) -> str:
    resource, _filter = RESOURCE_FILTERS[table_name]
    return FhirFilter.objects.create(auto_generated=True,
                                     fhir_resource=resource,
                                     filter=_filter,
                                     name=f'{str(export.uuid)[:8]}_{table_name}_(auto generated)',
                                     owner=export.owner).uuid


@shared_task
def create_cohort_subsets(export_id: str, tables: List[Dict], auth_headers: Dict) -> Dict[str, Dict[str, str]]:
    export = get_export_by_id(export_id)
    cohort_subsets_tables = {}
    for table in tables:
        fhir_filter_id = table.get("fhir_filter")
        cohort_source_id = table.get("cohort_result_source")
        cohort_source = cohort_source_id and CohortResult.objects.get(pk=cohort_source_id) or None
        table_name = table.get("table_name")
        if cohort_source and table_name in TABLES_REQUIRING_SUB_COHORTS and not fhir_filter_id:
            fhir_filter_id = force_generate_fhir_filter(export=export,
                                                        table_name=table_name)
        if cohort_source and fhir_filter_id and table_name not in EXCLUDED_TABLES:
            cohort_subset = cohort_service.create_cohort_subset(auth_headers=auth_headers,
                                                                owner_id=export.owner_id,
                                                                table_name=table_name,
                                                                fhir_filter_id=fhir_filter_id,
                                                                source_cohort=cohort_source)
            _logger.info(f"Export[{export_id}] Launched cohort subset creation for table `{table_name}`.")
            cohort_subsets_tables[table_name] = str(cohort_subset.uuid)
    return cohort_subsets_tables


@shared_task
def relaunch_cohort_subsets(export_id: str, failed_cohort_subsets_ids: List[str], auth_headers: Dict):
    failure_reason = None
    for cs in CohortResult.objects.filter(uuid__in=failed_cohort_subsets_ids):
        try:
            cohort_service.handle_cohort_creation(cs, auth_headers)
            _logger.info(f"Export[{export_id}] Retry - relaunched cohort subset {cs.name}")
        except ServerError:
            failure_reason = f"The cohort subset `{cs.name}` has failed"
            _logger_err.exception(f"Export[{export_id}] Retry - Error relaunching cohort subset {cs.name}")
            break
    return failure_reason
