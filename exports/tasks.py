import logging
import os
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from requests import RequestException

from admin_cohort.celery import celery_app
from admin_cohort.tools.celery_periodic_task_helper import ensure_single_task
from admin_cohort.types import JobStatus
from exports.exceptions import StorageProviderException
from exports.models import ExportRequest
from exports.emails import exported_csv_files_deleted, push_email_notification, export_request_received
from exports.exporters.hive_exporter import HiveExporter
from exports.exporters.csv_exporter import CSVExporter
from exports.services.export_manager import ExportCleaner
from exports.exporters.types import ExportType

_logger = logging.getLogger('django.request')
_celery_logger = logging.getLogger('celery.app')
env = os.environ

EXPORT_CSV_PATH = env.get('EXPORT_CSV_PATH')
HIVE_DB_FOLDER = env.get('HIVE_DB_FOLDER')


def log_export_request_task(er_id, msg):
    _celery_logger.info(f"[ExportTask] [ExportRequest: {er_id}] {msg}")


@shared_task
def launch_export_task(export_id: str, export_model):
    export = export_model.objects.get(pk=export_id)
    exporter = CSVExporter()
    if export.output_format == ExportType.HIVE:
        exporter = HiveExporter()
    start = timezone.now()
    exporter.handle_export(export=export)
    exporter.finalize(export=export, start_time=start)


@celery_app.task()
@ensure_single_task("delete_exported_csv_files")
def delete_exported_csv_files():
    d = timezone.now() - timedelta(days=settings.DAYS_TO_KEEP_EXPORTED_FILES)
    export_requests = ExportRequest.objects.filter(request_job_status=JobStatus.finished,
                                                   output_format=ExportType.CSV,
                                                   is_user_notified=True,
                                                   insert_datetime__lte=d,
                                                   cleaned_at__isnull=True)
    for export_request in export_requests:
        try:
            ExportCleaner().delete_file(file_name=export_request.target_full_path)
        except (RequestException, StorageProviderException) as e:
            _logger.exception(f"ExportRequest {export_request.id}: {e}")

        notification_data = dict(recipient_name=export_request.owner.display_name,
                                 recipient_email=export_request.owner.email,
                                 cohort_id=export_request.cohort_id)
        push_email_notification(base_notification=exported_csv_files_deleted, **notification_data)
        export_request.cleaned_at = timezone.now()
        export_request.save()


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
