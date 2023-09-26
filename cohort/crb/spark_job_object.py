from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cohort.crb.enums import Mode
    from cohort.crb import CohortQuery


@dataclass
class SparkJobObject:
    cohort_definition_name: str
    cohort_definition_syntax: CohortQuery
    mode: Mode
    owner_entity_id: str
