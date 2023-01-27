from time import sleep

from celery import shared_task, current_task

import cohort.conf_cohort_job_api as cohort_job_api
from admin_cohort.models import JobStatus
from admin_cohort.settings import COHORT_LIMIT
from cohort.models import CohortResult, DatedMeasure
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.tools import log_count_task, log_create_task


@shared_task
def create_cohort_task(auth_headers: dict, json_query: str, cohort_uuid: str):
    # TODO: Useful? Is the create transaction already closed? latency in database saving (when calling this task)
    cohort_result: CohortResult = None
    tries = 0
    while cohort_result is None and tries <= 5:
        cohort_result = CohortResult.objects.filter(uuid=cohort_uuid).first()
        if not cohort_result:
            log_create_task(cohort_uuid, f"Error: could not find CohortResult to update after {tries - 1} sec")
            tries = tries + 1
            sleep(1)

    if not cohort_result:
        log_create_task(cohort_uuid, "Error: could not find CohortResult to update after 5 sec")
        return

    log_create_task(cohort_uuid, "Asking CRB to create cohort")
    resp = cohort_job_api.post_create_cohort(auth_headers=auth_headers, json_query=json_query, cr_uuid=cohort_uuid)

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
    # in case of small latency in database saving (when calling this task)
    dm: DatedMeasure = None
    tries = 0
    while dm is None and tries <= 5:
        dm = DatedMeasure.objects.filter(uuid=dm_uuid).first()
        if dm is None:
            log_count_task(dm_uuid, f"Error: could not find DatedMeasure to update after {tries - 1} sec")
            tries = tries + 1
            sleep(1)

    if dm is None:
        log_count_task(dm_uuid, "Error: could not find DatedMeasure to update")
        return

    dm.count_task_id = current_task.request.id or ""
    dm.request_job_status = JobStatus.pending
    dm.save()

    global_estimate = dm.mode == GLOBAL_DM_MODE

    log_count_task(dm_uuid, f"Asking CRB to get {'global ' if global_estimate else ''}count")

    resp = cohort_job_api.post_count_cohort(json_query=json_query,
                                            auth_headers=auth_headers,
                                            dated_measure=dm_uuid,
                                            global_estimate=global_estimate)
    if resp.success:
        if not global_estimate:
            dm.measure = resp.count
        else:
            dm.measure_min = resp.count_min
            dm.measure_max = resp.count_max

        dm.fhir_datetime = resp.fhir_datetime
        dm.request_job_status = resp.fhir_job_status
        dm.request_job_duration = resp.job_duration
        dm.request_job_id = resp.fhir_job_id
        dm.save()
        log_count_task(dm_uuid, f"Dated Measure count: {dm.measure}")
        log_count_task(dm_uuid, "Dated measure updated")
    else:
        dm.request_job_status = resp.fhir_job_status
        dm.request_job_fail_msg = resp.err_msg
        dm.request_job_duration = resp.job_duration
        dm.request_job_id = resp.fhir_job_id
        dm.save()
        log_count_task(dm_uuid, resp.err_msg)
