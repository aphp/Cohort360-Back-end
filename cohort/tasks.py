import logging
from smtplib import SMTPException

from celery import shared_task, current_task

import cohort.services.conf_cohort_job_api as cohort_job_api
from admin_cohort import celery_app
from admin_cohort.types import JobStatus
from cohort.models import CohortResult, DatedMeasure, FeasibilityStudy
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.services.emails import send_email_notif_feasibility_report_requested, send_email_notif_error_feasibility_report
from cohort.services.decorators import locked_instance_task

_logger = logging.getLogger('django.request')


@shared_task
def create_cohort_task(auth_headers: dict, json_query: str, cohort_uuid: str):
    cr = CohortResult.objects.get(uuid=cohort_uuid)
    cr.create_task_id = current_task.request.id or ""
    cr.save()
    cohort_job_api.post_create_cohort(cr_uuid=cohort_uuid,
                                      json_query=json_query,
                                      auth_headers=auth_headers)


@shared_task
@locked_instance_task
def get_count_task(auth_headers=None, json_query=None, dm_uuid=None):
    dm = DatedMeasure.objects.get(uuid=dm_uuid)
    dm.count_task_id = current_task.request.id or ""
    dm.request_job_status = JobStatus.pending
    dm.save()
    cohort_job_api.post_count_cohort(dm_uuid=dm_uuid,
                                     json_query=json_query,
                                     auth_headers=auth_headers,
                                     global_estimate=dm.mode == GLOBAL_DM_MODE)


@shared_task
def get_feasibility_count_task(fs_uuid: str, json_query: str, auth_headers: dict) -> bool:
    fs = FeasibilityStudy.objects.get(uuid=fs_uuid)
    fs.count_task_id = current_task.request.id or ""
    fs.save()
    resp = cohort_job_api.post_count_for_feasibility(fs_uuid=fs_uuid,
                                                     json_query=json_query,
                                                     auth_headers=auth_headers)
    return resp.success


@shared_task
def send_email_notification_task(feasibility_count_task_succeeded: bool, *args, **kwargs):
    fs = FeasibilityStudy.objects.get(uuid=args[0])
    try:
        if feasibility_count_task_succeeded:
            send_email_notif_feasibility_report_requested(request_name=fs.request_query_snapshot.request.name,
                                                          owner=fs.owner)
        else:
            send_email_notif_error_feasibility_report(request_name=fs.request_query_snapshot.request.name,
                                                      owner=fs.owner)
    except (ValueError, SMTPException) as e:
        _logger.exception(f"FeasibilityStudy [{fs.uuid}] - Couldn't send email to user. {e}")


@shared_task
def cancel_previously_running_dm_jobs(dm_uuid: str):
    dm = DatedMeasure.objects.get(pk=dm_uuid)
    rqs = dm.request_query_snapshot
    running_dms = rqs.dated_measures.exclude(uuid=dm.uuid)\
                                    .filter(request_job_status__in=(JobStatus.started, JobStatus.pending))\
                                    .prefetch_related('cohorts', 'global_cohorts')
    for dm in running_dms:
        if dm.cohorts.all() or dm.global_cohorts.all():
            continue
        job_status = dm.request_job_status
        try:
            if job_status == JobStatus.started:
                new_status = cohort_job_api.cancel_job(dm.request_job_id)
                dm.request_job_status = new_status
            else:
                celery_app.control.revoke(dm.count_task_id)
                dm.request_job_status = JobStatus.cancelled
        except Exception as e:
            msg = f"Error while cancelling {job_status} job [{dm.request_job_id}] DM [{dm.uuid}] - {e}"
            _logger.exception(msg)
            dm.request_job_status = JobStatus.failed
            dm.request_job_fail_msg = msg
        finally:
            dm.save()
