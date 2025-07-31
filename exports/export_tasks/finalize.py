import logging
from typing import Optional

from celery import shared_task

from exporters.enums import ExportTypes
from exporters.exceptions import HiveDBOwnershipException
from exporters.exporters.hive_exporter import HiveExporter
from exports.tools import get_export_by_id


_logger = logging.getLogger('info')


@shared_task
def finalize_export(failure_reason: Optional[str], export_id: str) -> Optional[str]:
    if failure_reason is not None:
        _logger.info(f"Export[{export_id}]<{finalize_export.__name__}> Failed, task ignored")
        return failure_reason
    export = get_export_by_id(export_id)
    if export.output_format == ExportTypes.HIVE:
        _logger.info(f"Export[{export_id}] Finalizing export...")
        hive_exporter = HiveExporter()
        export_owner = export.datalab.name
        try:
            hive_exporter.change_db_ownership(export=export, db_user=export_owner)
            _logger.info(f"Export[{export_id}] Attributed Hive database to user `{export_owner}`")
        except HiveDBOwnershipException as e:
            failure_reason = str(e)
    return failure_reason