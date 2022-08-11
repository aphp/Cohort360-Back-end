from datetime import timedelta, datetime
import time
from typing import List
import environ
from celery import shared_task
from django.utils import timezone

from admin_cohort.celery import app
from admin_cohort.models import NewJobStatus
from exports import conf_exports
from exports.emails import email_info_request_done, email_info_request_deleted
from exports.example_conf_exports import HdfsServerUnreachableError, \
    ApiJobResponse
from exports.models import ExportRequest, SUCCESS_STATUS, FAILED_STATUS, \
    DENIED_STATUS, ExportType


env = environ.Env()
EXPORT_CSV_PATH = env('EXPORT_CSV_PATH')


def log_export_request_task(id, msg):
    print(f"[ExportTask] [ExportRequest: {id}] {msg}")


def manage_exception(er: ExportRequest, e: Exception, msg: str,
                     start: datetime):
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
    if er.new_request_job_status in [
        NewJobStatus.pending, NewJobStatus.validated, NewJobStatus.new
    ]:
        er.new_request_job_status = NewJobStatus.failed
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
    status_resp = ApiJobResponse(NewJobStatus.pending)

    while errs < 5 and not status_resp.has_ended:
        time.sleep(5)
        log_export_request_task(
            er.id, f"Asking for status of job {er.request_job_id}.")
        try:
            status_resp: ApiJobResponse = conf_exports.get_job_status(
                er.request_job_id)
            log_export_request_task(
                er.id,
                f"Status received: {status_resp.status} - "
                f"Err: {status_resp.err}")
            if er.new_request_job_status != status_resp.status:
                er.new_request_job_status = status_resp.status
                er.save()
        except Exception as e:
            log_export_request_task(er.id, f"Status not received: {e}")
            errs += 1
            err_msg = str(e)

    if status_resp.status != NewJobStatus.finished:
        raise Exception(status_resp.err or "no 'err' value returned.")
    elif errs >= 5:
        raise Exception(f"5 times internal error during task -> {err_msg}")


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
        er: ExportRequest = ExportRequest.objects.get(er_id)
    except Exception as e:
        log_export_request_task(
            er_id,
            f"Could not find export request to launch with id {er_id}: {e}")
        return

    t = timezone.now()
    log_export_request_task(er.id, "Sending request to Infra API.")
    if er.output_format == ExportType.CSV:
        er.target_name = f"{EXPORT_CSV_PATH}/{er.target_unix_account.name}" \
                         f"_{timezone.now().strftime('%Y%m%d_%H%M%S%f')}"
    else:
        er.target_name = f"{er.target_unix_account.name}" \
                     f"_{timezone.now().strftime('%Y%m%d_%H%M%S%f')}"
    er.save()

    try:
        conf_exports.prepare_for_export(er)
    except Exception as e:
        manage_exception(er, e, f"Error while preparing for export {er.id}", t)
        return

    try:
        job_id = conf_exports.post_export(er)
    except Exception as e:
        manage_exception(er, e, f"Could not post export {er.id}", t)
        return

    er.new_request_job_status = NewJobStatus.pending
    er.request_job_id = job_id
    er.save()
    log_export_request_task(er.id, f"Request sent, job {job_id} is now "
                                   f"{NewJobStatus.pending}")

    try:
        wait_for_job(er)
    except Exception as e:
        manage_exception(er, e, f"Failure during export job {er.id}", t)
        return

    log_export_request_task(er.id, "Export job finished, now concluding.")

    try:
        conf_exports.conclude_export(er)
    except Exception as e:
        manage_exception(er, e, f"Could not conclude export {er.id}", t)
        return

    er.request_job_duration = timezone.now() - t
    er.save()

    email_info_request_done(er)


@app.task()
def check_jobs():
    """
    Queries ExportRequest that have csv output, have finished
    and whom the owner has not been notified yet.
    Will update its new_request_job_status, warn the owner by email and update
    the ExportRequest with 'is_user_notified'
    @return: None
    """
    reqs = list(ExportRequest.objects.filter(
        status__in=[SUCCESS_STATUS, FAILED_STATUS, DENIED_STATUS],
        output_format=ExportType.CSV.value,
        is_user_notified=False
    ))

    old_status_to_new = {SUCCESS_STATUS: NewJobStatus.finished.value,
                         FAILED_STATUS: NewJobStatus.failed.value,
                         DENIED_STATUS: NewJobStatus.denied.value}

    for req in reqs:
        req.new_request_job_status = old_status_to_new[req.status]
        req.save()
        try:
            email_info_request_done(req)
            req.is_user_notified = True
            req.save()
        except Exception as e:
            print(e)


@app.task()
def clean_jobs():
    """
    Queries ExportRequest that have csv output,
    have finished for a number of days and whom the owner has been notified.
    Will delete its content taht was stored, warn the owner by email,
    and update cleaned_at values
    @return: None
    """
    from admin_cohort.settings import EXPORT_DAYS_BEFORE_DELETE
    q = ExportRequest.objects.all()
    reqs: List[ExportRequest] = list((
            q.filter(status=SUCCESS_STATUS)
            | q.filter(new_request_job_status=NewJobStatus.finished.value)
    ).filter(
        output_format=ExportType.CSV.value,
        is_user_notified=True,
        review_request_datetime__lte=(
            timezone.now() - timedelta(days=EXPORT_DAYS_BEFORE_DELETE)),
        cleaned_at__isnull=True,
    ))

    for req in reqs:
        user = req.owner

        if user is None:
            print(f"Error with req {req.id}: has no owner")
            continue
        try:
            conf_exports.delete_file(req.target_full_path)
            email_info_request_deleted(req, user.email)

            req.cleaned_at = timezone.now()
            req.save()
        except HdfsServerUnreachableError:
            msg = "Hdfs servers are unreachable or in stand-by",
            print(f"Error with req {req.id}: {msg}")
        except Exception as e:
            print(f"Error with req {req.id}: {e}")
