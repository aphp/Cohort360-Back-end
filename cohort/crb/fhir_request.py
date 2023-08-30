from dataclasses import field, dataclass

from cohort.crb.enums import CriteriaType
from cohort.crb.ranges import TemporalConstraint, Criteria
from cohort.crb.source_population import SourcePopulation


@dataclass
class FhirRequest:
    cohort_uuid: str | None = None
    cohort_name: str | None = None
    source_population: SourcePopulation | None = None
    type: CriteriaType | None = None
    request: Criteria | None = None
    temporal_constraints: list[TemporalConstraint] = field(default_factory=list)
