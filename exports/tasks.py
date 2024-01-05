import logging
import os
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from requests import RequestException, HTTPError

from admin_cohort.celery import celery_app
from admin_cohort.settings import EXPORT_CSV_PATH
from admin_cohort.tools.celery_periodic_task_helper import ensure_single_task
from admin_cohort.types import JobStatus
from exports import conf_exports
from .models import ExportRequest, Export
from .emails import exported_csv_files_deleted, export_request_succeeded, push_email_notification
from .types import ExportType, HdfsServerUnreachableError

_logger_err = logging.getLogger('django.request')
_celery_logger = logging.getLogger('celery.app')
env = os.environ

HIVE_DB_FOLDER = env.get('HIVE_DB_FOLDER')


def log_export_request_task(er_id, msg):
    _celery_logger.info(f"[ExportTask] [ExportRequest: {er_id}] {msg}")


@shared_task
def launch_request(er_id: int):
    try:
        export_request = ExportRequest.objects.get(pk=er_id)
    except ExportRequest.DoesNotExist:
        log_export_request_task(er_id, f"Could not find export request to launch with ID {er_id}")
        return
    now = timezone.now()
    output_format = export_request.output_format
    log_export_request_task(er_id, "Sending request to Infra API.")
    if output_format == ExportType.CSV:
        export_request.target_name = f"{export_request.owner.pk}_{now.strftime('%Y%m%d_%H%M%S%f')}"
        export_request.target_location = EXPORT_CSV_PATH
    else:
        export_request.target_name = f"{export_request.target_unix_account.name}_{now.strftime('%Y%m%d_%H%M%S%f')}"
    export_request.save()

    if output_format == ExportType.HIVE:
        try:
            conf_exports.prepare_hive_db(export_request)
        except RequestException as e:
            conf_exports.mark_export_request_as_failed(export_request, e, f"Error while preparing for export {er_id}", now)
            return

    try:
        job_id = conf_exports.post_export(export_request)
        export_request.request_job_status = JobStatus.pending
        export_request.request_job_id = job_id
        export_request.save()
        log_export_request_task(er_id, f"Request sent, job {job_id} is now {JobStatus.pending}")
    except RequestException as e:
        conf_exports.mark_export_request_as_failed(export_request, e, f"Could not post export {er_id}", now)
        return

    try:
        conf_exports.wait_for_export_job(export_request)
    except HTTPError as e:
        conf_exports.mark_export_request_as_failed(export_request, e, f"Failure during export job {er_id}", now)
        return

    log_export_request_task(er_id, "Export job finished, now concluding.")

    if output_format == ExportType.HIVE:
        try:
            conf_exports.conclude_export_hive(export_request)
        except RequestException as e:
            conf_exports.mark_export_request_as_failed(export_request, e, f"Could not conclude export {er_id}", now)
            return
    export_request.request_job_duration = timezone.now() - now
    export_request.save()
    notification_data = dict(recipient_name=export_request.owner.displayed_name,
                             recipient_email=export_request.owner.email,
                             export_request_id=export_request.id,
                             cohort_id=export_request.cohort_id,
                             cohort_name=export_request.cohort_name,
                             output_format=export_request.output_format,
                             database_name=export_request.target_name,
                             selected_tables=export_request.tables.values_list("omop_table_name", flat=True))
    push_email_notification(base_notification=export_request_succeeded, **notification_data)


@shared_task
def launch_export_task(export_id: str):
    export = Export.objects.get(pk=export_id)
    now = timezone.now()
    output_format = export.output_format
    if output_format == ExportType.CSV:
        export.target_name = f"{export.owner.pk}_{now.strftime('%Y%m%d_%H%M%S%f')}"
        export.target_location = EXPORT_CSV_PATH
    else:
        export.target_name = f"{export.datalab.name}_{now.strftime('%Y%m%d_%H%M%S%f')}"
        export.target_location = HIVE_DB_FOLDER
    export.save()

    if output_format == ExportType.HIVE:
        try:
            conf_exports.prepare_hive_db(export_request=export)
        except RequestException as e:
            conf_exports.mark_export_request_as_failed(export, e, f"Error while preparing for export {export_id}", now)
            return

    try:
        job_id = conf_exports.post_export_v1(export=export)
        export.request_job_status = JobStatus.pending
        export.request_job_id = job_id
        export.save()
        log_export_request_task(export_id, f"Request sent, job {job_id} is now {JobStatus.pending}")
    except RequestException as e:
        conf_exports.mark_export_request_as_failed(export, e, f"Could not post export {export_id}", now)
        return

    try:
        conf_exports.wait_for_export_job(export)
    except HTTPError as e:
        conf_exports.mark_export_request_as_failed(export, e, f"Failure during export job {export_id}", now)
        return

    log_export_request_task(export_id, "Export job finished, now concluding.")

    if output_format == ExportType.HIVE:
        try:
            conf_exports.conclude_export_hive(export)
        except RequestException as e:
            conf_exports.mark_export_request_as_failed(export, e, f"Could not conclude export {export_id}", now)
            return
    export.request_job_duration = timezone.now() - now
    export.save()
    notification_data = dict(recipient_name=export.owner.displayed_name,
                             recipient_email=export.owner.email,
                             export_request_id=export_id,
                             cohort_id=output_format == ExportType.CSV and export.cohort_id or None,
                             cohort_name=None,
                             output_format=output_format,
                             database_name=export.target_name,
                             selected_tables=export.export_tables.values_list("name", flat=True))
    push_email_notification(base_notification=export_request_succeeded, **notification_data)


@celery_app.task()
@ensure_single_task("delete_export_requests_csv_files")
def delete_export_requests_csv_files():
    d = timezone.now() - timedelta(days=settings.DAYS_TO_DELETE_CSV_FILES)
    export_requests = ExportRequest.objects.filter(request_job_status=JobStatus.finished,
                                                   output_format=ExportType.CSV,
                                                   is_user_notified=True,
                                                   insert_datetime__lte=d,
                                                   cleaned_at__isnull=True)
    for export_request in export_requests:
        owner = export_request.owner
        if not owner:
            _logger_err.error(f"ExportRequest {export_request.id} has no owner")
            continue
        try:
            conf_exports.delete_file(export_request.target_full_path)
            notification_data = dict(recipient_name=export_request.owner.displayed_name,
                                     recipient_email=export_request.owner.email,
                                     cohort_id=export_request.cohort_id)
            push_email_notification(base_notification=exported_csv_files_deleted, **notification_data)
            export_request.cleaned_at = timezone.now()
            export_request.save()
        except (RequestException, HdfsServerUnreachableError) as e:
            _logger_err.exception(f"ExportRequest {export_request.id}: {e}")
