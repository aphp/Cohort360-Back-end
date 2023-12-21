import logging

from celery import shared_task, current_task

import cohort.services.conf_cohort_job_api as cohort_job_api
from admin_cohort import celery_app
from admin_cohort.types import JobStatus
from admin_cohort.settings import COHORT_LIMIT
from cohort.models import CohortResult, DatedMeasure, FeasibilityStudy
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.services.misc import log_count_task, log_create_task

_logger = logging.getLogger('django.request')


@shared_task
def create_cohort_task(auth_headers: dict, json_query: str, cohort_uuid: str):
    cohort_result = CohortResult.objects.get(uuid=cohort_uuid)
    resp = cohort_job_api.post_create_cohort(cr_uuid=cohort_uuid,
                                             json_query=json_query,
                                             auth_headers=auth_headers)

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
def get_count_task(auth_headers: dict, json_query: str, dm_uuid: str):
    dm = DatedMeasure.objects.get(uuid=dm_uuid)
    dm.count_task_id = current_task.request.id or ""
    dm.request_job_status = JobStatus.pending
    dm.save()
    resp = cohort_job_api.post_count_cohort(dm_uuid=dm_uuid,
                                            json_query=json_query,
                                            auth_headers=auth_headers,
                                            global_estimate=dm.mode == GLOBAL_DM_MODE)
    if resp.success:
        dm.request_job_id = resp.fhir_job_id
    else:
        dm.request_job_status = JobStatus.failed
        dm.request_job_fail_msg = resp.err_msg
    dm.save()
    log_count_task(dm_uuid, resp.success and "DatedMeasure updated" or resp.err_msg)


@shared_task
def get_feasibility_count_task(auth_headers: dict, json_query: str, fs_uuid: str):
    resp = cohort_job_api.post_count_for_feasibility(fs_uuid=fs_uuid,
                                                     json_query=json_query,
                                                     auth_headers=auth_headers)
    log_count_task(fs_uuid, resp.success and "FeasibilityStudy updated" or resp.err_msg)


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
