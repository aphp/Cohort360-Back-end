from celery import chain

from admin_cohort.types import JobStatus
from cohort.models import CohortResult, DatedMeasure, FeasibilityStudy
from cohort.services.misc import get_authorization_header
from cohort_operators.exceptions import ServerError
from cohort_operators.tasks import cancel_previous_count_jobs, count_cohort_task, feasibility_count_task, send_email_notification_task


class CohortCounter:

    @staticmethod
    def launch_count(dm: DatedMeasure, request) -> None:
        cancel_previous_count_jobs.s(dm_uuid=dm.uuid).apply_async()
        try:
            count_cohort_task.s(auth_headers=get_authorization_header(request),
                                json_query=dm.request_query_snapshot.serialized_query,
                                dm_uuid=dm.uuid) \
                             .apply_async()
        except Exception as e:
            dm.delete()
            raise ServerError("INTERNAL ERROR: Could not launch count request") from e

    @staticmethod
    def launch_global_count(cohort: CohortResult, request) -> None:
        dm_global = cohort.dated_measure_global
        try:
            count_cohort_task.s(auth_headers=get_authorization_header(request),
                                json_query=cohort.request_query_snapshot.serialized_query,
                                dm_uuid=dm_global.uuid) \
                .apply_async()
        except Exception as e:
            dm_global.request_job_fail_msg = f"ERROR: Could not launch cohort global count: {e}"
            dm_global.request_job_status = JobStatus.failed
            dm_global.save()

    @staticmethod
    def launch_feasibility_study_count(fs: FeasibilityStudy, request) -> None:
        try:
            chain(*(feasibility_count_task.s(fs.uuid,
                                             fs.request_query_snapshot.serialized_query,
                                             get_authorization_header(request)),
                    send_email_notification_task.s(fs.uuid)))()
        except Exception as e:
            fs.delete()
            raise ServerError("INTERNAL ERROR: Could not launch feasibility request") from e

