import logging
import time
from datetime import timedelta, datetime

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from requests import RequestException, HTTPError

from admin_cohort.celery import celery_app
from admin_cohort.settings import EXPORT_CSV_PATH
from admin_cohort.tools.celery_periodic_task_helper import ensure_single_task
from admin_cohort.types import JobStatus
from exports import conf_exports
from .emails import email_info_request_done, email_info_request_deleted
from .models import ExportRequest
from .types import ExportType, HdfsServerUnreachableError, ApiJobResponse

_logger_err = logging.getLogger('django.request')
_celery_logger = logging.getLogger('celery.app')


def log_export_request_task(er_id, msg):
    _celery_logger.info(f"[ExportTask] [ExportRequest: {er_id}] {msg}")


def manage_exception(er: ExportRequest, e: Exception, msg: str, start: datetime):
    """
    Will update er with context msg and exception e,
    new 'failed' status if not done yet and job_duration given start datetime
    Also logs the info
    @param er:
    @param e:
    @param msg:
    @param start:
    @return:
    """
    err_msg = f"{msg}: {e}"
    er.request_job_fail_msg = err_msg
    if er.request_job_status in [JobStatus.pending, JobStatus.validated, JobStatus.new]:
        er.request_job_status = JobStatus.failed
    er.request_job_duration = timezone.now() - start
    er.save()
    log_export_request_task(er.id, err_msg)


def wait_for_export_job(er: ExportRequest):
    errors_count = 0
    error_msg = ""
    status_resp = ApiJobResponse(JobStatus.pending)

    while errors_count < 5 and not status_resp.has_ended:
        time.sleep(5)
        log_export_request_task(er.id, f"Asking for status of job {er.request_job_id}.")
        try:
            status_resp: ApiJobResponse = conf_exports.get_job_status(service="bigdata", job_id=er.request_job_id)
            log_export_request_task(er.id, f"Status received: {status_resp.status} - Err: {status_resp.err or ''}")
            if er.request_job_status != status_resp.status:
                er.request_job_status = status_resp.status
                er.save()
        except RequestException as e:
            log_export_request_task(er.id, f"Status not received: {e}")
            errors_count += 1
            error_msg = str(e)

    if status_resp.status != JobStatus.finished:
        raise HTTPError(status_resp.err or "No 'err' value returned.")
    elif errors_count >= 5:
        raise HTTPError(f"5 times internal error during task -> {error_msg}")


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
            manage_exception(export_request, e, f"Error while preparing for export {er_id}", now)
            return

    try:
        job_id = conf_exports.post_export(export_request)
        export_request.request_job_status = JobStatus.pending
        export_request.request_job_id = job_id
        export_request.save()
        log_export_request_task(er_id, f"Request sent, job {job_id} is now {JobStatus.pending}")
    except RequestException as e:
        manage_exception(export_request, e, f"Could not post export {er_id}", now)
        return

    try:
        wait_for_export_job(export_request)
    except HTTPError as e:
        manage_exception(export_request, e, f"Failure during export job {er_id}", now)
        return

    log_export_request_task(er_id, "Export job finished, now concluding.")

    if output_format == ExportType.HIVE:
        try:
            conf_exports.conclude_export_hive(export_request)
        except RequestException as e:
            manage_exception(export_request, e, f"Could not conclude export {er_id}", now)
            return

    export_request.request_job_duration = timezone.now() - now
    export_request.save()
    email_info_request_done(export_request)


@celery_app.task()
@ensure_single_task("delete_export_requests_csv_files")
def delete_export_requests_csv_files():
    d = timezone.now() - timedelta(days=settings.DAYS_TO_DELETE_CSV_FILES)
    export_requests = ExportRequest.objects.filter(request_job_status=JobStatus.finished,
                                                   output_format=ExportType.CSV,
                                                   is_user_notified=True,
                                                   review_request_datetime__lte=d,
                                                   cleaned_at__isnull=True)
    for export_request in export_requests:
        user = export_request.owner
        if not user:
            _logger_err.error(f"ExportRequest {export_request.id} has no owner")
            continue
        try:
            conf_exports.delete_file(export_request.target_full_path)
            email_info_request_deleted(export_request, user.email)
            export_request.cleaned_at = timezone.now()
            export_request.save()
        except HdfsServerUnreachableError:
            _logger_err.exception(f"ExportRequest {export_request.id} - HDFS servers are unreachable or in stand-by")
        except RequestException as e:
            _logger_err.exception(f"ExportRequest {export_request.id}: {e}")
