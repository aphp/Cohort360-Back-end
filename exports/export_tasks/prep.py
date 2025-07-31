import logging
from typing import Optional

from celery import shared_task

from exporters.enums import ExportTypes
from exporters.exceptions import CreateHiveDBException, HiveDBOwnershipException
from exporters.exporters.hive_exporter import HiveExporter
from exports.tools import get_export_by_id


_logger = logging.getLogger('info')


@shared_task
def prepare_export(failure_reason: Optional[str], export_id: str) -> Optional[str]:
    if failure_reason is not None:
        _logger.info(f"Export[{export_id}]<{prepare_export.__name__}> Failed, task ignored")
        return failure_reason
    export = get_export_by_id(export_id)
    if export.output_format == ExportTypes.HIVE:
        _logger.info(f"Export[{export_id}] Preparing Hive database")
        hive_exporter = HiveExporter()
        try:
            hive_exporter.create_db(export=export)
            _logger.info(f"Export[{export_id}] DB '{export.target_name}' created.")
            hive_exporter.change_db_ownership(export=export, db_user=hive_exporter.user)
            _logger.info(f"Export[{export_id}] `{hive_exporter.user}` was granted rights on DB `{export.target_name}`.")
        except (CreateHiveDBException, HiveDBOwnershipException) as e:
            failure_reason = f"Error while preparing DB for export: {e}"
    return failure_reason
