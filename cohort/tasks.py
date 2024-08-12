import logging

from celery import shared_task, current_task

from admin_cohort import celery_app
from admin_cohort.types import JobStatus
from cohort.models import CohortResult, DatedMeasure, FeasibilityStudy, RequestQuerySnapshot
from cohort.services.base_service import load_operator
from cohort.services.emails import send_email_notif_feasibility_report_requested, send_email_notif_error_feasibility_report, \
    send_email_notif_feasibility_report_ready, send_email_notif_count_request_refreshed
from cohort.services.utils import locked_instance_task, get_feasibility_study_by_id, send_email_notification, ServerError

_logger = logging.getLogger('django.request')


@shared_task
def create_cohort(cohort_id: str, json_query: str, auth_headers: dict, cohort_creator_cls: str) -> None:
    cr = CohortResult.objects.get(uuid=cohort_id)
    cr.create_task_id = current_task.request.id or ""
    cr.save()
    cohort_creator = load_operator(cohort_creator_cls)
    cohort_creator.launch_cohort_creation(cohort_id=cohort_id,
                                          json_query=json_query,
                                          auth_headers=auth_headers)


@shared_task
@locked_instance_task
def count_cohort(dm_id: str, json_query: str, auth_headers: dict, cohort_counter_cls: str, global_estimate=False) -> None:
    dm = DatedMeasure.objects.get(uuid=dm_id)
    dm.count_task_id = current_task.request.id or ""
    dm.request_job_status = JobStatus.pending
    dm.save()
    cohort_counter = load_operator(cohort_counter_cls)
    cohort_counter.launch_dated_measure_count(dm_id=dm_id,
                                              json_query=json_query,
                                              auth_headers=auth_headers,
                                              global_estimate=global_estimate)


@shared_task
def cancel_previous_count_jobs(dm_id: str, cohort_counter_cls: str):
    dm = DatedMeasure.objects.get(pk=dm_id)
    rqs = dm.request_query_snapshot
    running_dms = rqs.dated_measures.exclude(uuid=dm.uuid)\
                                    .filter(request_job_status__in=(JobStatus.started,
                                                                    JobStatus.pending))\
                                    .prefetch_related('cohorts', 'global_cohorts')
    cohort_counter = load_operator(cohort_counter_cls)
    for dm in running_dms:
        if dm.cohorts.all() or dm.global_cohorts.all():
            continue
        job_status = dm.request_job_status
        try:
            if job_status == JobStatus.started.value:
                new_status = cohort_counter.cancel_job(job_id=dm.request_job_id)
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
def feasibility_study_count(fs_id: str, json_query: str, auth_headers: dict, cohort_counter_cls: str) -> bool:
    fs = FeasibilityStudy.objects.get(uuid=fs_id)
    fs.count_task_id = current_task.request.id or ""
    fs.save()
    cohort_counter = load_operator(cohort_counter_cls)
    return cohort_counter.launch_feasibility_study_count(fs_id=fs_id,
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


@shared_task
def send_email_count_request_refreshed(snapshot_id: str) -> None:
    snapshot = RequestQuerySnapshot.objects.get(pk=snapshot_id)
    send_email_notification(notification=send_email_notif_count_request_refreshed,
                            request_name=f"{snapshot.request.name} (version {snapshot.version})",
                            owner=snapshot.owner)


@shared_task
def refresh_count_request(dm_id: str, translated_query: str, cohort_counter_cls: str):
    dm = DatedMeasure.objects.get(uuid=dm_id)
    _logger.info(f"Request Snapshot Refreshing [{dm.request_query_snapshot.uuid}]")
    try:
        dm.count_task_id = current_task.request.id or ""
        dm.request_job_status = JobStatus.pending
        dm.save()
        cohort_counter = load_operator(cohort_counter_cls)
        cohort_counter.refresh_dated_measure_count(translated_query=translated_query)
    except Exception as e:
        raise ServerError("Error refreshing request") from e

