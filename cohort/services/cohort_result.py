from django.core.exceptions import ValidationError
from django.db import transaction

from cohort.conf_cohort_job_api import get_authorization_header
from cohort.models import CohortResult, FhirFilter
from cohort.tasks import create_cohort_task


class CohortResultService:

    @staticmethod
    def build_query(cohort_source_id: str, cohort_uuid: str, fhir_search_filter: str) -> str:
        cohort_resource_type = "cohort_resource_type"
        resource_type = "resource_type"
        query = {"_type": "request",
                 "resourceType": cohort_resource_type,
                 "cohortUuid": cohort_uuid,
                 "request": {"_id": 1,
                             "_type": "basicResource",
                             "filterFhir": fhir_search_filter,
                             # "filterSolr": "fq=gender:f&fq=deceased:false&fq=active:true",    todo: rempli par le CRB
                             "isInclusive": True,
                             "resourceType": resource_type
                             },
                 "sourcePopulation": {"caresiteCohortList": [cohort_source_id]}
                 }
        return str(query)

    @staticmethod
    def create_cohort_subset(owner_id: str, table_name: str, cohort_id: str, filter_id: str, http_request) -> CohortResult:
        cohort_subset = CohortResult.objects.create(name=f"{table_name}_{cohort_id}",
                                                    owner_id=owner_id)
        fhir_filter = FhirFilter.objects.get(pk=filter_id)

        with transaction.atomic():
            query = CohortResultService.build_query(cohort_source_id=cohort_id,
                                                    cohort_uuid=cohort_subset.uuid,
                                                    fhir_search_filter=fhir_filter.filter)
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
