from admin_cohort.types import JobStatus
from cohort.models import DatedMeasure, CohortResult
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.services.base_service import CommonService
from cohort.services.request_refresh_schedule import requests_refresher_service
from cohort.services.utils import get_authorization_header, ServerError
from cohort.services.ws_event_manager import ws_send
from cohort.tasks import cancel_previous_count_jobs, count_cohort


class DatedMeasureService(CommonService):
    job_type = "count"

    def handle_count(self, dm: DatedMeasure, request) -> None:
        cancel_previous_count_jobs.s(dm_id=dm.uuid, cohort_counter_cls=self.operator_cls).apply_async()
        try:
            count_cohort.s(dm_id=dm.uuid,
                           json_query=dm.request_query_snapshot.serialized_query,
                           auth_headers=get_authorization_header(request),
                           cohort_counter_cls=self.operator_cls) \
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
            ws_send(instance=dm, job_name='count', extra_info={"request_job_status": dm.request_job_status,
                                                               "request_job_fail_msg": dm.request_job_fail_msg,
                                                               "measure": dm.measure})

    @staticmethod
    def update_refresh_schedule(dm: DatedMeasure) -> None:
        requests_refresher_service.update_refreshing_metadata(dm=dm)


dm_service = DatedMeasureService()
