import logging
import time
from datetime import timedelta, datetime

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from requests import RequestException, HTTPError

from admin_cohort.celery import app
from admin_cohort.settings import EXPORT_CSV_PATH
from admin_cohort.types import JobStatus
from exports import conf_exports
from .emails import email_info_request_done, email_info_request_deleted
from .models import ExportRequest
from .types import ExportType, HdfsServerUnreachableError, ApiJobResponse

_log_info = logging.getLogger('info')
_log_err = logging.getLogger('django.request')


def log_export_request_task(er_id, msg):
    _log_info.info(f"[ExportTask] [ExportRequest: {er_id}] {msg}")


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


def wait_for_job(er: ExportRequest):
    """
    Will initialize the Job response with empty values
    Then will call conf_exports.get_job_status untill the resp.status warns
    that the job has ended
    If 5 errors while retrieving the status, or an ending status not 'finished',
    will raise Exception
    @param er: ExportRequest to ask for the job status
    @return: None
    """
    errs = 0
    err_msg = ""
    status_resp = ApiJobResponse(JobStatus.pending)

    while errs < 5 and not status_resp.has_ended:
        time.sleep(5)
        log_export_request_task(er.id, f"Asking for status of job {er.request_job_id}.")
        try:
            status_resp: ApiJobResponse = conf_exports.get_job_status(er.request_job_id)
            log_export_request_task(er.id, f"Status received: {status_resp.status} - Err: {status_resp.err or ''}")
            if er.request_job_status != status_resp.status:
                er.request_job_status = status_resp.status
                er.save()
        except RequestException as e:
            log_export_request_task(er.id, f"Status not received: {e}")
            errs += 1
            err_msg = str(e)

    if status_resp.status != JobStatus.finished:
        raise HTTPError(status_resp.err or "No 'err' value returned.")
    elif errs >= 5:
        raise HTTPError(f"5 times internal error during task -> {err_msg}")


@shared_task
def launch_request(er_id: int):
    """
    Defines the ExportRequest target_name and then,
    given functions in conf_exports.py, prepares and starts the export,
    wait for it to end and concludes with post process
    If an exception happens, logs it and end the task
    @param er_id: id of ExportRequest to launch a job for
    @return: None
    """
    try:
        er = ExportRequest.objects.get(pk=er_id)
    except ExportRequest.DoesNotExist:
        log_export_request_task(er_id, f"Could not find export request to launch with ID {er_id}")
        return
    now = timezone.now()
    log_export_request_task(er.id, "Sending request to Infra API.")
    if er.output_format == ExportType.CSV:
        er.target_name = f"{er.owner.pk}_{now.strftime('%Y%m%d_%H%M%S%f')}"
        er.target_location = EXPORT_CSV_PATH
    else:
        er.target_name = f"{er.target_unix_account.name}_{now.strftime('%Y%m%d_%H%M%S%f')}"
    er.save()

    try:
        conf_exports.prepare_for_export(er)
    except RequestException as e:
        manage_exception(er, e, f"Error while preparing for export {er.id}", now)
        return

    try:
        job_id = conf_exports.post_export(er)
    except RequestException as e:
        manage_exception(er, e, f"Could not post export {er.id}", now)
        return

    er.request_job_status = JobStatus.pending
    er.request_job_id = job_id
    er.save()
    log_export_request_task(er.id, f"Request sent, job {job_id} is now {JobStatus.pending}")

    try:
        wait_for_job(er)
    except HTTPError as e:
        manage_exception(er, e, f"Failure during export job {er.id}", now)
        return

    log_export_request_task(er.id, "Export job finished, now concluding.")

    try:
        conf_exports.conclude_export(er)
    except RequestException as e:
        manage_exception(er, e, f"Could not conclude export {er.id}", now)
        return

    er.request_job_duration = timezone.now() - now
    er.save()
    email_info_request_done(er)


@app.task()
def delete_export_requests_csv_files():
    """
    Get export requests with: CSV output, finished for a number of days
    and the owner has been notified.
    Delete content that was stored, notify the owner by email,
    and update cleaned_at field
    @return: None
    """
    d = timezone.now() - timedelta(days=settings.DAYS_TO_DELETE_CSV_FILES)
    ers = ExportRequest.objects.filter(request_job_status=JobStatus.finished,
                                       output_format=ExportType.CSV,
                                       is_user_notified=True,
                                       review_request_datetime__lte=d,
                                       cleaned_at__isnull=True)
    for er in ers:
        user = er.owner
        if not user:
            _log_err.error(f"ExportRequest {er.id} has no owner")
            continue
        try:
            conf_exports.delete_file(er.target_full_path)
            email_info_request_deleted(er, user.email)
            er.cleaned_at = timezone.now()
            er.save()
        except HdfsServerUnreachableError:
            _log_err.exception(f"ExportRequest {er.id} - HDFS servers are unreachable or in stand-by")
        except RequestException as e:
            _log_err.exception(f"ExportRequest {er.id}: {e}")
