import logging
from typing import List, Dict

from celery import shared_task

from exports.tools import get_export_by_id
from exports.models import ExportTable


_logger = logging.getLogger('info')


@shared_task
def create_export_tables(cohort_subsets_tables: Dict[str, str], export_id: str, tables: List[Dict]) -> None:
    export = get_export_by_id(export_id)
    _logger.info(f"Export[{export_id}] Creating tables...")
    try:
        for table in tables:
            table_name = table.get("table_name")
            cohort_subset_id = cohort_subsets_tables.get(table_name)
            t = ExportTable.objects.create(export=export,
                                           name=table_name,
                                           fhir_filter_id=table.get("fhir_filter"),
                                           cohort_result_source_id=table.get("cohort_result_source"),
                                           cohort_result_subset_id=cohort_subset_id,
                                           columns=table.get("columns"),
                                           pivot_merge=bool(table.get("pivot_merge")),
                                           pivot_merge_columns=table.get("pivot_merge_columns"),
                                           pivot_merge_ids=table.get("pivot_merge_ids")
                                           )
            _logger.info(f"Export[{export_id}] Table `{t.name}` created")
    except Exception:
        _logger.exception(f"Export[{export_id}] Error creating tables")
        raise
