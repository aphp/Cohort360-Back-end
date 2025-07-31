import logging
from typing import Optional

from celery import shared_task
from django.conf import settings

from admin_cohort.types import JobStatus
from exporters.notifications import export_failed_notif_for_owner, export_failed_notif_for_admins
from exports.emails import push_email_notification
from exports.models import Export
from exports.tools import get_export_by_id, get_cohort

_logger = logging.getLogger('info')


def notify_export_owner(export: Export, base_notification_data: dict) -> None:
    notification_data = {**base_notification_data,
                         "recipient_name": export.owner.display_name,
                         "recipient_email": export.owner.email
                         }
    try:
        push_email_notification(base_notification=export_failed_notif_for_owner, **notification_data)
    except Exception as e:
        _logger.error(f"Export[{export.pk}] Error sending export failure notification: {e}")
    else:
        export.is_user_notified = True
        export.save()


def notify_admins(export: Export, base_notification_data: dict) -> None:
    notification_data = {**base_notification_data,
                         "export_id": export.pk,
                         "export_date": export.created_at.isoformat(),
                         "job_id": export.request_job_id,
                         "job_duration": export.request_job_duration,
                         "host": settings.BACKEND_URL,
                         }
    try:
        push_email_notification(base_notification=export_failed_notif_for_admins, **notification_data)
    except Exception:
        _logger.error(f"Export[{export.pk}] Error sending export failure notification to admins")


@shared_task
def mark_export_as_failed(failure_reason: Optional[str], export_id: str) -> None:
    if failure_reason:
        _logger.info(f"Export[{export_id}] Failed: {failure_reason}")
        export = get_export_by_id(export_id)
        export.request_job_status = JobStatus.failed
        export.request_job_fail_msg = failure_reason
        export.save()
        cohort = get_cohort(export=export)
        base_notification_data = {"cohort_id": cohort.group_id if cohort else None,
                                  "cohort_name": cohort.name if cohort else None,
                                  "error_message": failure_reason
                                  }
        notify_export_owner(export, base_notification_data)
        notify_admins(export, base_notification_data)