import logging
from typing import Optional

from celery import shared_task
from django.db.models.query_utils import Q

from admin_cohort.types import JobStatus
from exporters.exporters.base_exporter import BaseExporter
from exports.tools import get_export_by_id


_logger = logging.getLogger('info')


@shared_task
def send_export_request(failure_reason: Optional[str], export_id: str) -> Optional[str]:
    if failure_reason is not None:
        _logger.info(f"Export[{export_id}]<{send_export_request.__name__}> Failed, task ignored")
        return failure_reason
    export = get_export_by_id(export_id)
    _logger.info(f"Export[{export_id}] Sending export request")
    if export.output_format == "hive":
        params = {"output": {"type": export.output_format,
                             "databaseName": export.target_name
                             }
                  }
    else:   # csv, xlsx
        params = {"joinOnPrimaryKey": export.group_tables,
                  "output": {"type": export.output_format,
                             "filePath": f"{export.target_full_path}.zip"
                             }
                  }
        pivot_merge = list(export.export_tables.filter(pivot_merge=True).values_list("name", flat=True))

        if pivot_merge:
            params["pivotMerge"] = pivot_merge

        pivot_merge_2 = []
        for t in export.export_tables.filter(Q(pivot_merge_columns__isnull=False)
                                             | Q(pivot_merge_ids__isnull=False)):
            d = {"tableName": t.name}
            if t.pivot_merge_columns:
                d["pivotedColumnsToKeep"] = t.pivot_merge_columns
            if t.pivot_merge_ids:
                d["idsToMerge"] = t.pivot_merge_ids
            pivot_merge_2.append(d)

        if pivot_merge_2:
            params["pivotMerge"] = pivot_merge_2

    params = {**params, "overwrite": True}
    exporter = BaseExporter()
    job_id = exporter.send_export(export=export, params=params)
    if job_id is None:
        failure_reason = f"Got an invalid Job ID: `{job_id}`"
        return failure_reason
    export.request_job_status = JobStatus.pending
    export.request_job_id = job_id
    export.save()
    _logger.info(f"Export[{export_id}] Request sent, job `{job_id}` is now {JobStatus.pending}")
    return failure_reason
