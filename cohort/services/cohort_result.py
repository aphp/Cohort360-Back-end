import json

from django.conf import settings
from django.db import transaction

from admin_cohort.types import JobStatus
from cohort.models import CohortResult, FhirFilter, DatedMeasure, RequestQuerySnapshot
from cohort.serializers import WSJobStatus, JobName
from cohort.services.base_service import CommonService
from cohort.services.dated_measure import dm_service
from cohort.services.utils import ServerError
from admin_cohort.services.ws_event_manager import WebsocketManager, WebSocketMessageType
from cohort.tasks import create_cohort


class CohortResultService(CommonService):
    job_type = "create"

    @staticmethod
    def build_query(cohort_source_id: str, fhir_filter_id: str = None) -> str:
        resource_type, f_filter = "Patient", ""
        if fhir_filter_id is not None:
            fhir_filter = FhirFilter.objects.get(pk=fhir_filter_id)
            resource_type = fhir_filter.fhir_resource
            f_filter = fhir_filter.filter

        query = {"_type": "request",
                 "resourceType": resource_type,
                 "sourcePopulation": {"caresiteCohortList": [cohort_source_id]},
                 "request": {"_id": 0,
                             "_type": "basicResource",
                             "isInclusive": True,
                             "filterFhir": f_filter,
                             "resourceType": resource_type
                             }
                 }
        return json.dumps(query)

    def create_cohort_subset(self,
                             auth_headers: dict,
                             owner_id: str,
                             table_name: str,
                             source_cohort: CohortResult,
                             fhir_filter_id: str) -> CohortResult:
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

        query = self.build_query(cohort_source_id=source_cohort.group_id,
                                 fhir_filter_id=fhir_filter_id
                                 )
        new_rqs = copy_query_snapshot(source_cohort.request_query_snapshot)
        new_dm = copy_dated_measure(source_cohort.dated_measure)
        cohort_subset = CohortResult.objects.create(is_subset=True,
                                                    name=f"{table_name}_{source_cohort.group_id}",
                                                    owner_id=owner_id,
                                                    dated_measure=new_dm,
                                                    request_query_snapshot=new_rqs)
        with transaction.atomic():
            self.handle_cohort_creation(cohort_subset, auth_headers)
        return cohort_subset

    @staticmethod
    def count_active_jobs():
        active_statuses = [JobStatus.new,
                           JobStatus.validated,
                           JobStatus.started,
                           JobStatus.pending]
        return CohortResult.objects.filter(request_job_status__in=active_statuses) \
            .count()

    def handle_cohort_creation(self, cohort: CohortResult, auth_headers: dict, global_estimate: bool=False) -> None:
        if global_estimate:
            dm_service.handle_global_count(cohort, auth_headers)
        try:
            if cohort.parent_cohort and cohort.sampling_ratio:
                json_query = self.build_query(cohort_source_id=cohort.parent_cohort.group_id)
                count = (cohort.parent_cohort.dated_measure.measure or 0) * cohort.sampling_ratio
            else:
                json_query = cohort.request_query_snapshot.serialized_query
                count = cohort.dated_measure.measure or 0

            job_status = count >= settings.COHORT_SIZE_LIMIT and JobStatus.long_pending or JobStatus.pending
            cohort.request_job_status = job_status
            cohort.save()

            create_cohort.s(cohort_id=cohort.pk,
                            json_query=json_query,
                            auth_headers=auth_headers,
                            cohort_creator_cls=self.operator_cls,
                            sampling_ratio=cohort.sampling_ratio) \
                         .apply_async()
        except Exception as e:
            cohort.delete()
            raise ServerError("Could not launch cohort creation") from e

    def handle_patch_cohort(self, cohort: CohortResult, data: dict) -> None:
        self.operator.handle_patch_cohort(cohort, data)

    def handle_cohort_post_update(self, cohort: CohortResult, caller: str) -> None:
        self.operator.handle_cohort_post_update(cohort, caller)

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
                      'result_size': cohort.dated_measure.measure,
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
