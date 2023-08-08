import logging
from time import sleep

from celery import shared_task, current_task

import cohort.conf_cohort_job_api as cohort_job_api
from admin_cohort import celery_app
from admin_cohort.types import JobStatus
from admin_cohort.settings import COHORT_LIMIT
from cohort.models import CohortResult, DatedMeasure
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.tools import log_count_task, log_create_task

_logger = logging.getLogger('django.request')


@shared_task
def create_cohort_task(auth_headers: dict, json_query: str, cohort_uuid: str):
    try:
        cohort_result = CohortResult.objects.get(uuid=cohort_uuid)
    except CohortResult.DoesNotExist:
        log_create_task(cohort_uuid, "Error: could not find CohortResult")
        return

    log_create_task(cohort_uuid, "Asking CRB to create cohort")
    resp = cohort_job_api.post_create_cohort(auth_headers=auth_headers,
                                             json_query=json_query,
                                             cr_uuid=cohort_uuid)

    cohort_result.create_task_id = current_task.request.id or ""
    if resp.success:
        cohort_result.request_job_id = resp.fhir_job_id
        count = cohort_result.dated_measure.measure
        cohort_result.request_job_status = count >= COHORT_LIMIT and JobStatus.long_pending or JobStatus.pending
    else:
        cohort_result.request_job_status = JobStatus.failed
        cohort_result.request_job_fail_msg = resp.err_msg
    cohort_result.save()
    log_create_task(cohort_uuid, resp.success and "CohortResult updated" or resp.err_msg)


@shared_task
def cancel_previously_running_dm_jobs(auth_headers: dict, dm_uuid: str):
    dm = DatedMeasure.objects.get(pk=dm_uuid)
    rqs = dm.request_query_snapshot
    running_dms = rqs.dated_measures.exclude(uuid=dm.uuid)\
                                    .filter(request_job_status__in=(JobStatus.started, JobStatus.pending))\
                                    .prefetch_related('cohort', 'restricted_cohort')
    for dm in running_dms:
        if dm.cohort.all() or dm.restricted_cohort.all():
            continue
        job_status = dm.request_job_status
        try:
            if job_status == JobStatus.started:
                new_status = cohort_job_api.cancel_job(dm.request_job_id, auth_headers)
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
def get_count_task(auth_headers: dict, json_query: str, dm_uuid: str):
    try:
        dm = DatedMeasure.objects.get(uuid=dm_uuid)
    except DatedMeasure.DoesNotExist:
        log_count_task(dm_uuid, "Error: could not find DatedMeasure")
        return

    dm.count_task_id = current_task.request.id or ""
    dm.request_job_status = JobStatus.pending
    dm.save()

    global_estimate = dm.mode == GLOBAL_DM_MODE

    log_count_task(dm_uuid, f"Asking CRB to get {'global ' if global_estimate else ''}count")

    resp = cohort_job_api.post_count_cohort(auth_headers=auth_headers,
                                            json_query=json_query,
                                            dm_uuid=dm_uuid,
                                            global_estimate=global_estimate)

    if resp.success:
        dm.request_job_id = resp.fhir_job_id
    else:
        dm.request_job_status = JobStatus.failed
        dm.request_job_fail_msg = resp.err_msg
    dm.save()
