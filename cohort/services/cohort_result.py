import json

from django.db import transaction

from admin_cohort.types import JobStatus
from cohort.models import CohortResult, FhirFilter, DatedMeasure, RequestQuerySnapshot
from cohort.services.cohort_managers import CohortCountManager, CohortCreationManager
from cohort.services.ws_event_manager import ws_send_to_client


class CohortResultService:

    @staticmethod
    def build_query(cohort_source_id: str, fhir_filter_id: str) -> str:
        fhir_filter = FhirFilter.objects.get(pk=fhir_filter_id)
        query = {"_type": "request",
                 "sourcePopulation": {"caresiteCohortList": [cohort_source_id]},
                 "request": {"_id": 0,
                             "_type": "andGroup",
                             "isInclusive": True,
                             "criteria": [{"_id": 1,
                                           "_type": "basicResource",
                                           "isInclusive": True,
                                           "filterFhir": fhir_filter.filter,
                                           "resourceType": fhir_filter.fhir_resource
                                           }]
                             }
                 }
        return json.dumps(query)

    def create_cohort_subset(self, request, owner_id: str, table_name: str, source_cohort: CohortResult, fhir_filter_id: str) -> CohortResult:
        def copy_query_snapshot(snapshot: RequestQuerySnapshot) -> RequestQuerySnapshot:
            return RequestQuerySnapshot.objects.create(owner=snapshot.owner,
                                                       request=snapshot.request,
                                                       perimeters_ids=snapshot.perimeters_ids,
                                                       serialized_query=query)

        def copy_dated_measure(dm: DatedMeasure) -> DatedMeasure:
            return DatedMeasure.objects.create(mode=dm.mode,
                                               owner=dm.owner,
                                               request_query_snapshot=new_rqs,
                                               measure=dm.measure)

        query = self.build_query(source_cohort.group_id, fhir_filter_id)
        new_rqs = copy_query_snapshot(source_cohort.request_query_snapshot)
        new_dm = copy_dated_measure(source_cohort.dated_measure)
        cohort_subset = CohortResult.objects.create(is_subset=True,
                                                    name=f"{table_name}_{source_cohort.group_id}",
                                                    owner_id=owner_id,
                                                    dated_measure_id=new_dm,
                                                    request_query_snapshot=new_rqs)
        with transaction.atomic():
            CohortCreationManager().handle_cohort_creation(cohort_subset, request)
        return cohort_subset

    @staticmethod
    def count_active_jobs():
        active_statuses = [JobStatus.new,
                           JobStatus.validated,
                           JobStatus.started,
                           JobStatus.pending]
        return CohortResult.objects.filter(request_job_status__in=active_statuses)\
                                   .count()

    @staticmethod
    def proceed_with_cohort_creation(request, cohort: CohortResult):
        if request.data.pop("global_estimate", False):
            CohortCountManager().handle_global_count(cohort, request)
        CohortCreationManager().handle_cohort_creation(cohort, request)

    @staticmethod
    def handle_patch_data(cohort: CohortResult, data: dict) -> None:
        CohortCreationManager().handle_patch_data(cohort, data)

    @staticmethod
    def handle_cohort_post_update(cohort: CohortResult, data) -> None:
        CohortCreationManager().handle_cohort_post_update(cohort, data)

    @staticmethod
    def ws_send_to_client(cohort: CohortResult) -> None:
        cohort.refresh_from_db()
        global_dm = cohort.dated_measure_global
        extra_info = {'group_id': cohort.group_id}  # todo: [front] rename `fhir_group_id` to `group_id`
        if global_dm:
            extra_info['global'] = {'measure_min': global_dm.measure_min,
                                    'measure_max': global_dm.measure_max
                                    }
        ws_send_to_client(instance=cohort, job_name='create', extra_info=extra_info)


cohort_service = CohortResultService()
