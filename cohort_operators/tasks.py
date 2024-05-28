import logging
from smtplib import SMTPException

from celery import shared_task

from cohort.models import CohortResult
from cohort_operators.emails import send_email_notif_large_cohort_ready


_logger = logging.getLogger("info")
_logger_err = logging.getLogger("django.request")


@shared_task
def notify_large_cohort_ready(cohort_id: str) -> None:
    cohort = CohortResult.objects.get(pk=cohort_id)
    try:
        send_email_notif_large_cohort_ready(cohort.name, cohort.group_id, cohort.owner)
    except (ValueError, SMTPException) as e:
        _logger_err.exception(f"Cohort[{cohort_id}]: Couldn't send email to user after ETL patch: {e}")
    else:
        _logger.info(f"Cohort[{cohort_id}]: Successfully updated from ETL")
