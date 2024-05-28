import logging

from celery import shared_task, current_task

from admin_cohort import celery_app
from admin_cohort.types import JobStatus
from cohort.models import CohortResult, DatedMeasure, FeasibilityStudy
from cohort.services.emails import send_email_notif_feasibility_report_requested, send_email_notif_error_feasibility_report, \
    send_email_notif_feasibility_report_ready
from cohort.services.misc import locked_instance_task, get_feasibility_study_by_id, send_email_notification


_logger = logging.getLogger('django.request')


@shared_task
def create_cohort(cohort_id: str, json_query: str, auth_headers: dict, operator_cls: type) -> None:
    cr = CohortResult.objects.get(uuid=cohort_id)
    cr.create_task_id = current_task.request.id or ""
    cr.save()
    operator_cls().launch_cohort_creation(cr_uuid=cohort_id,
                                          json_query=json_query,
                                          auth_headers=auth_headers)


@shared_task
@locked_instance_task
def count_cohort(dm_id: str, json_query: str, auth_headers: dict, operator_cls: type, global_estimate=False) -> None:
    dm = DatedMeasure.objects.get(uuid=dm_id)
    dm.count_task_id = current_task.request.id or ""
    dm.request_job_status = JobStatus.pending
    dm.save()
    operator_cls().launch_count(dm_id=dm_id,
                                json_query=json_query,
                                auth_headers=auth_headers,
                                global_estimate=global_estimate)


@shared_task
def cancel_previous_count_jobs(dm_uuid: str, operator_cls: type):
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
                new_status = operator_cls().cancel_job(job_id=dm.request_job_id)
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


@shared_task
def feasibility_study_count(fs_id: str, json_query: str, auth_headers: dict, operator_cls: type) -> bool:
    fs = FeasibilityStudy.objects.get(uuid=fs_id)
    fs.count_task_id = current_task.request.id or ""
    fs.save()
    return operator_cls().launch_feasibility_study_count(fs_id=fs_id,
                                                         json_query=json_query,
                                                         auth_headers=auth_headers)


@shared_task
def send_feasibility_study_notification(feasibility_count_task_succeeded: bool, *args, **kwargs):
    fs = get_feasibility_study_by_id(fs_id=args[0])
    if feasibility_count_task_succeeded:
        notif = send_email_notif_feasibility_report_requested
    else:
        notif = send_email_notif_error_feasibility_report
    send_email_notification(notification=notif,
                            request_name=fs.request_query_snapshot.request.name,
                            owner=fs.owner,
                            fs_id=fs.uuid)


@shared_task
def send_email_feasibility_report_ready(fs_id: str) -> None:
    fs = get_feasibility_study_by_id(fs_id=fs_id)
    send_email_notification(notification=send_email_notif_feasibility_report_ready,
                            request_name=fs.request_query_snapshot.request.name,
                            owner=fs.owner,
                            fs_id=fs_id)


@shared_task
def send_email_feasibility_report_error(fs_id: str) -> None:
    fs = get_feasibility_study_by_id(fs_id=fs_id)
    send_email_notification(notification=send_email_notif_error_feasibility_report,
                            request_name=fs.request_query_snapshot.request.name,
                            owner=fs.owner,
                            fs_id=fs_id)
