import logging

from celery import shared_task

from exports.models import ExportRequest
from exports.emails import push_email_notification
from exporters.notifications import csv_export_received, hive_export_received

_logger = logging.getLogger('django.request')

NOTIFICATIONS = {"csv": csv_export_received,
                 "hive": hive_export_received
                 }


@shared_task
def notify_export_received(export_id: str) -> None:
    export = ExportRequest.objects.get(pk=export_id)
    export_type = export.output_format

    try:
        notification_data = dict(recipient_name=export.owner.display_name,
                                 recipient_email=export.owner.email,
                                 cohort_id=export.cohort_id,
                                 cohort_name=export.cohort_name,
                                 output_format=export_type,
                                 selected_tables=export.tables.values_list("omop_table_name", flat=True))
        push_email_notification(base_notification=NOTIFICATIONS.get(export_type), **notification_data)
    except Exception as e:
        _logger.error(f"Error sending export confirmation email - {e}")
