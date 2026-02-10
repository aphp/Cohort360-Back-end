import logging
import time
from typing import Optional

from celery import shared_task

from admin_cohort.types import JobStatus
from exports.tools import get_export_by_id


_logger = logging.getLogger('info')


@shared_task
def await_cohort_subsets(failure_reason: str, export_id: str) -> Optional[str]:
    if failure_reason is not None:
        _logger.info(f"Export[{export_id}]<{await_cohort_subsets.__name__}> Failed, task ignored")
        return failure_reason
    export = get_export_by_id(export_id)
    _logger.info(f"Export[{export_id}] Checking if all cohort subsets have been created...")
    cohort_subsets = [t.cohort_result_subset
                      for t in export.export_tables.filter(cohort_result_subset__isnull=False)]
    if not cohort_subsets:
        _logger.info(f"Export[{export_id}] No cohort subsets were expected.")
        return None

    cohorts_count, finished_cohorts = len(cohort_subsets), 0

    while finished_cohorts != cohorts_count:
        time.sleep(10)
        for c in cohort_subsets:
            c.refresh_from_db()
            if c.request_job_status == JobStatus.failed:
                failure_reason = "One or more cohort subsets have failed"
                _logger.info(f"Export[{export_id}] Aborting export... reason: {failure_reason}")
                return failure_reason
            if c.request_job_status == JobStatus.finished:
                finished_cohorts += 1
    _logger.info(f"Export[{export_id}] All cohort subsets were successfully created.")
    return failure_reason

