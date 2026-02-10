import logging

from celery import shared_task

from exporters.notifications import EXPORT_RECEIVED_NOTIFICATIONS
from exports.emails import push_email_notification
from exports.tools import get_export_by_id, get_selected_tables

_logger = logging.getLogger('info')


@shared_task
def notify_export_received(export_id: str, cohort_id: str, cohort_name: str) -> None:
    export = get_export_by_id(export_id)
    export_type = export.output_format
    try:
        notification_data = {"recipient_name": export.owner.display_name,
                             "recipient_email": export.owner.email,
                             "retried": export.retried,
                             "cohort_id": cohort_id,
                             "cohort_name": cohort_name,
                             "selected_tables": get_selected_tables(export=export)
                             }
        push_email_notification(base_notification=EXPORT_RECEIVED_NOTIFICATIONS[export_type],
                                **notification_data)
        _logger.info(f"Export[{export.uuid}] Confirmation email sent")
    except Exception as e:
        _logger.error(f"Export[{export.uuid}] Error sending confirmation email - {e}")
