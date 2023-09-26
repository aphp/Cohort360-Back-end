from dataclasses import dataclass

from cohort.crb.enums import Mode
from cohort.crb.cohort_query import CohortQuery


@dataclass
class SparkJobObject:
    cohort_definition_name: str
    cohort_definition_syntax: CohortQuery
    mode: Mode
    owner_entity_id: str

