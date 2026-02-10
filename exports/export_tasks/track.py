import logging
from typing import Optional

from celery import shared_task

from admin_cohort.types import JobStatus
from exporters.exporters.base_exporter import BaseExporter
from exports.tools import get_export_by_id


_logger = logging.getLogger('info')


@shared_task
def track_export_job(failure_reason: Optional[str], export_id: str) -> Optional[str]:
    if failure_reason is not None:
        _logger.info(f"Export[{export_id}]<{track_export_job.__name__}> Failed, task ignored")
        return failure_reason
    export = get_export_by_id(export_id)
    _logger.info(f"Export[{export_id}] Tracking export with job id `{export.request_job_id}`")
    exporter = BaseExporter()
    job_status = exporter.track_job(export=export)
    if job_status == JobStatus.finished:
        _logger.info(f"Export[{export_id}] Export finished")
    else:
        failure_reason = f"Ended with status `{job_status}`"
    return failure_reason
