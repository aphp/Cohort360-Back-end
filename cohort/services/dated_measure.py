from typing import Tuple

from admin_cohort.types import JobStatus
from cohort.models import DatedMeasure, CohortResult
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.services.base_service import CommonService
from cohort.services.utils import get_authorization_header, ServerError
from cohort.services.ws_event_manager import ws_send_to_client
from cohort.tasks import cancel_previous_count_jobs, count_cohort


class DatedMeasureService(CommonService):
    job_type = "count"

    def handle_count(self, dm: DatedMeasure, request) -> None:
        cancel_previous_count_jobs.s(dm_id=dm.uuid, operator=self.operator).apply_async()
        try:
            count_cohort.s(dm_id=dm.uuid,
                           json_query=dm.request_query_snapshot.serialized_query,
                           auth_headers=get_authorization_header(request),
                           operator=self.operator) \
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
                           operator=self.operator,
                           global_estimate=True) \
                        .apply_async()
        except Exception as e:
            raise ServerError("Could not launch count request") from e
        cohort.dated_measure_global = dm_global
        cohort.save()

    def handle_patch_dated_measure(self, dm, data) -> Tuple[bool, None | Exception]:
        success, exception = True, None
        try:
            self.operator().handle_patch_dated_measure(dm, data)
        except ValueError as ve:
            self.mark_dm_as_failed(dm=dm, reason=str(ve))
            success, exception = False, ve
        return success, exception

    def mark_dm_as_failed(self, dm: DatedMeasure, reason: str) -> None:
        dm.request_job_status = JobStatus.failed
        dm.request_job_fail_msg = reason
        dm.save()
        self.ws_send_to_client(dm=dm, extra_info={"error": f"DM failed: {reason}"})

    def ws_push_to_client(self, dm: DatedMeasure) -> None:
        dm.refresh_from_db()
        self.ws_send_to_client(dm=dm, extra_info={"measure": dm.measure})

    @staticmethod
    def ws_send_to_client(dm: DatedMeasure, extra_info: dict) -> None:
        if not dm.is_global:
            ws_send_to_client(instance=dm, job_name='count', extra_info=extra_info)


dm_service = DatedMeasureService()
