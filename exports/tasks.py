import logging

from celery import shared_task

from admin_cohort.celery import celery_app
from admin_cohort.tools.celery_periodic_task_helper import ensure_single_task
from exports.models import ExportRequest, Export
from exports.emails import push_email_notification, export_request_received
from exports.services.export_manager import Exporter, ExportCleaner

_logger = logging.getLogger('django.request')


@shared_task
def launch_export_task(export_id: str, export_model: ExportRequest | Export):
    Exporter().handle_export(export_id=export_id, export_model=export_model)


@celery_app.task()
@ensure_single_task("delete_exported_csv_files")
def delete_exported_csv_files():
    ExportCleaner().delete_exported_files()


@shared_task
def notify_export_request_received(export_id: str) -> None:
    export = ExportRequest.objects.get(pk=export_id)
    try:
        notification_data = dict(recipient_name=export.owner.display_name,
                                 recipient_email=export.owner.email,
                                 cohort_id=export.cohort_id,
                                 cohort_name=export.cohort_name,
                                 output_format=export.output_format,
                                 selected_tables=export.tables.values_list("omop_table_name", flat=True))
        push_email_notification(base_notification=export_request_received, **notification_data)
    except Exception as e:
        _logger.error(f"Error sending export confirmation email - {e}")
