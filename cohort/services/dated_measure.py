from admin_cohort.types import JobStatus
from cohort.models import DatedMeasure, CohortResult
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.serializers import WSJobStatus, JobName
from cohort.services.base_service import CommonService
from cohort.services.utils import get_authorization_header, ServerError
from admin_cohort.services.ws_event_manager import WebsocketManager, WebSocketMessageType
from cohort.tasks import cancel_previous_count_jobs, count_cohort


class DatedMeasureService(CommonService):
    job_type = "count"

    def handle_count(self, dm: DatedMeasure, request) -> None:
        stage_details = request.data.get("stageDetails", None)
        cancel_previous_count_jobs.s(dm_id=dm.uuid, cohort_counter_cls=self.operator_cls).apply_async()
        try:
            count_cohort.s(dm_id=dm.uuid,
                           json_query=dm.request_query_snapshot.serialized_query,
                           auth_headers=get_authorization_header(request),
                           cohort_counter_cls=self.operator_cls,
                           stage_details=stage_details
                           ) \
                .apply_async()
        except Exception as e:
            dm.delete()
            raise ServerError("Could not launch count request") from e

    def handle_global_count(self, cohort: CohortResult, request) -> None:
        dm_global = DatedMeasure.objects.create(mode=GLOBAL_DM_MODE,
                                                owner=request.user,
                                                request_query_snapshot_id=request.data.get("request_query_snapshot"))
        try:
            count_cohort.s(dm_id=dm_global.uuid,
                           json_query=dm_global.request_query_snapshot.serialized_query,
                           auth_headers=get_authorization_header(request),
                           cohort_counter_cls=self.operator_cls,
                           global_estimate=True) \
                .apply_async()
        except Exception as e:
            raise ServerError("Could not launch count request") from e
        cohort.dated_measure_global = dm_global
        cohort.save()

    def handle_patch_dated_measure(self, dm, data) -> None:
        self.operator.handle_patch_dated_measure(dm, data)

    @staticmethod
    def mark_dm_as_failed(dm: DatedMeasure, reason: str) -> None:
        dm.request_job_status = JobStatus.failed
        dm.request_job_fail_msg = reason
        dm.save()

    @staticmethod
    def ws_send_to_client(dm: DatedMeasure) -> None:
        dm.refresh_from_db()
        if not dm.is_global:
            WebsocketManager.send_to_client(str(dm.owner_id), WSJobStatus(type=WebSocketMessageType.JOB_STATUS,
                                                                          status=dm.request_job_status,
                                                                          uuid=str(dm.uuid),
                                                                          job_name=JobName.COUNT,
                                                                          extra_info={"request_job_status": dm.request_job_status,
                                                                                      "request_job_fail_msg": dm.request_job_fail_msg,
                                                                                      "measure": dm.measure,
                                                                                      "extra": dm.extra
                                                                                      }))


dm_service = DatedMeasureService()
