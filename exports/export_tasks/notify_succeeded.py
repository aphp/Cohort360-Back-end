import logging
from typing import Optional

from celery import shared_task

from exporters.notifications import EXPORT_SUCCEEDED_NOTIFICATIONS
from exports.emails import push_email_notification
from exports.tools import get_export_by_id, get_cohort, get_selected_tables


_logger = logging.getLogger('info')


@shared_task
def notify_export_succeeded(failure_reason: Optional[str], export_id: str) -> Optional[str]:
    if failure_reason is not None:
        _logger.info(f"Export[{export_id}]<{notify_export_succeeded.__name__}> Failed, task ignored")
        return failure_reason
    export = get_export_by_id(export_id)
    cohort = get_cohort(export=export)
    notification_data = {"recipient_name": export.owner.display_name,
                         "recipient_email": export.owner.email,
                         "export_request_id": export_id,
                         "cohort_id": cohort.group_id if cohort else None,
                         "cohort_name": cohort.name if cohort else None,
                         "database_name": export.target_name,
                         "selected_tables": get_selected_tables(export=export)
                         }
    try:
        push_email_notification(base_notification=EXPORT_SUCCEEDED_NOTIFICATIONS.get(export.output_format),
                                **notification_data)
        _logger.info(f"Export[{export_id}] Export success email sent")
    except Exception as e:
        _logger.error(f"[Export {export_id}] Error sending export success email: {e}")
    else:
        export.is_user_notified = True
        export.save()
