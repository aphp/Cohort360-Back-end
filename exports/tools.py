from functools import lru_cache
from typing import List

from exports.models import Export


@lru_cache(maxsize=None)
def get_export_by_id(export_id: str) -> Export:
    try:
        return Export.objects.get(pk=export_id)
    except Export.DoesNotExist:
        raise ValueError(f'No export matches the given ID : {export_id}')


@lru_cache(maxsize=None)
def get_cohort(export: Export):
    sample_table = export.export_tables.filter(cohort_result_source__isnull=False).first()
    return sample_table.cohort_result_source


@lru_cache(maxsize=None)
def get_selected_tables(export: Export) -> List[str]:
    return export.export_tables.values_list("name", flat=True)
