import logging
from smtplib import SMTPException

from celery import shared_task

from cohort.models import CohortResult
from cohort_job_server.emails import send_email_notif_large_cohort_ready


logger = logging.getLogger(__name__)


@shared_task
def notify_large_cohort_ready(cohort_id: str) -> None:
    cohort = CohortResult.objects.get(pk=cohort_id)
    try:
        send_email_notif_large_cohort_ready(cohort.name, cohort.group_id, cohort.owner)
    except (ValueError, SMTPException) as e:
        logger.exception(f"Cohort[{cohort_id}]: Couldn't send email to user after ETL patch: {e}")
