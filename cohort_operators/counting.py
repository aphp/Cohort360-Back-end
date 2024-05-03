from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from .tasks import count_cohort_task


class CountingOperator:

    def launch_global_estimate(self, cohort: CohortResult, request):
        dm_global = cohort.dated_measure_global
        try:
            count_cohort_task.s(auth_headers=self.get_auth_headers(request),
                                json_query=cohort.request_query_snapshot.serialized_query,
                                dm_uuid=dm_global.uuid) \
                             .apply_async()
        except Exception as e:
            dm_global.request_job_fail_msg = f"ERROR: Could not launch cohort global count: {e}"
            dm_global.request_job_status = JobStatus.failed
            dm_global.save()