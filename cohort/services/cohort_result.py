from typing import Union

from django.core.exceptions import ValidationError
from django.db import transaction

from cohort.conf_cohort_job_api import get_authorization_header
from cohort.models import CohortResult, FhirFilter
from cohort.tasks import create_cohort_task


class CohortResultService:

    @staticmethod
    def build_query(cohort_source_id: str, cohort_uuid: str, fhir_filter: FhirFilter) -> str:
        query = {"_type": "request",
                 "resourceType": fhir_filter.fhir_resource,
                 "cohortUuid": cohort_uuid,
                 "request": {"_id": 1,
                             "_type": "basicResource",
                             "filterFhir": fhir_filter.filter,
                             # "filterSolr": "fq=gender:f&fq=deceased:false&fq=active:true",    todo: rempli par le CRB
                             "isInclusive": True,
                             "resourceType": fhir_filter.fhir_resource
                             },
                 "sourcePopulation": {"caresiteCohortList": [cohort_source_id]}
                 }
        return str(query)

    @staticmethod
    def create_cohort_subset(http_request, owner_id: str, table_name: str,
                             source_cohort: CohortResult, fhir_filter: Union[FhirFilter, None] = None) -> CohortResult:
        cohort_subset = CohortResult.objects.create(name=f"{table_name}_{source_cohort.fhir_group_id}",
                                                    owner_id=owner_id)
        with transaction.atomic():
            query = CohortResultService.build_query(cohort_source_id=source_cohort.fhir_group_id,
                                                    cohort_uuid=cohort_subset.uuid,
                                                    fhir_filter=fhir_filter)
            try:
                auth_headers = get_authorization_header(request=http_request)
                create_cohort_task.delay(auth_headers,
                                         query,
                                         cohort_subset.uuid)
            except Exception as e:
                cohort_subset.delete()
                raise ValidationError(f"Error creating the cohort subset for export: {e}")
        return cohort_subset


cohort_service = CohortResultService()
