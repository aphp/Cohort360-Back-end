from smtplib import SMTPException

from celery import shared_task

from cohort.models import CohortResult
from cohort_job_server.emails import send_email_notif_large_cohort_ready
from cohort_job_server.utils import _logger_err


@shared_task
def notify_large_cohort_ready(cohort_id: str) -> None:
    cohort = CohortResult.objects.get(pk=cohort_id)
    try:
        send_email_notif_large_cohort_ready(cohort.name, cohort.group_id, cohort.owner)
    except (ValueError, SMTPException) as e:
        _logger_err.exception(f"Cohort[{cohort_id}]: Couldn't send email to user after ETL patch: {e}")
