import json

from django.db import transaction

from admin_cohort.types import JobStatus
from cohort.models import CohortResult, FhirFilter, DatedMeasure, RequestQuerySnapshot
from cohort.serializers import WSJobStatus, JobName
from cohort.services.base_service import CommonService
from cohort.services.dated_measure import dm_service
from cohort.services.utils import get_authorization_header, ServerError
from admin_cohort.services.ws_event_manager import WebsocketManager, WebSocketMessageType
from cohort.tasks import create_cohort


class CohortResultService(CommonService):
    job_type = "create"

    @staticmethod
    def build_query(cohort_source_id: str, fhir_filter_id: str) -> str:
        fhir_filter = FhirFilter.objects.get(pk=fhir_filter_id)
        query = {"_type": "request",
                 "resourceType": fhir_filter.fhir_resource,
                 "sourcePopulation": {"caresiteCohortList": [cohort_source_id]},
                 "request": {"_id": 0,
                             "_type": "basicResource",
                             "isInclusive": True,
                             "filterFhir": fhir_filter.filter,
                             "resourceType": fhir_filter.fhir_resource
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
                                               measure=dm.measure,
                                               request_job_status=dm.request_job_status,
                                               request_job_duration=dm.request_job_duration)

        query = self.build_query(source_cohort.group_id, fhir_filter_id)
        new_rqs = copy_query_snapshot(source_cohort.request_query_snapshot)
        new_dm = copy_dated_measure(source_cohort.dated_measure)
        cohort_subset = CohortResult.objects.create(is_subset=True,
                                                    name=f"{table_name}_{source_cohort.group_id}",
                                                    owner_id=owner_id,
                                                    dated_measure=new_dm,
                                                    request_query_snapshot=new_rqs)
        with transaction.atomic():
            self.handle_cohort_creation(cohort_subset, request, False)
        return cohort_subset

    @staticmethod
    def count_active_jobs():
        active_statuses = [JobStatus.new,
                           JobStatus.validated,
                           JobStatus.started,
                           JobStatus.pending]
        return CohortResult.objects.filter(request_job_status__in=active_statuses) \
            .count()

    def handle_cohort_creation(self, cohort: CohortResult, request, global_estimate: bool) -> None:
        if global_estimate:
            dm_service.handle_global_count(cohort, request)
        try:
            create_cohort.s(cohort_id=cohort.pk,
                            json_query=cohort.request_query_snapshot.serialized_query,
                            auth_headers=get_authorization_header(request),
                            cohort_creator_cls=self.operator_cls) \
                .apply_async()

        except Exception as e:
            cohort.delete()
            raise ServerError("Could not launch cohort creation") from e

    def handle_patch_cohort(self, cohort: CohortResult, data: dict) -> None:
        self.operator.handle_patch_cohort(cohort, data)

    def handle_cohort_post_update(self, cohort: CohortResult, data: dict) -> None:
        self.operator.handle_cohort_post_update(cohort, data)

    @staticmethod
    def mark_cohort_as_failed(cohort: CohortResult, reason: str) -> None:
        cohort.request_job_status = JobStatus.failed
        cohort.request_job_fail_msg = reason
        cohort.save()

    @staticmethod
    def ws_send_to_client(cohort: CohortResult) -> None:
        cohort.refresh_from_db()
        global_dm = cohort.dated_measure_global
        extra_info = {'request_job_status': cohort.request_job_status,
                      'group_id': cohort.group_id,
                      'request_job_fail_msg': cohort.request_job_fail_msg
                      }
        if global_dm:
            extra_info['global'] = {'measure_min': global_dm.measure_min,
                                    'measure_max': global_dm.measure_max
                                    }

        WebsocketManager.send_to_client(str(cohort.owner_id), WSJobStatus(type=WebSocketMessageType.JOB_STATUS,
                                                                          status=cohort.request_job_status,
                                                                          uuid=str(cohort.uuid),
                                                                          job_name=JobName.CREATE,
                                                                          extra_info=extra_info))


cohort_service = CohortResultService()
