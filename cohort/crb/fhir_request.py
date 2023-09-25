from dataclasses import field, dataclass
from dataclasses import field

from pydantic import BaseModel, Field

from cohort.crb.criteria import Criteria
from cohort.crb.enums import CriteriaType
from cohort.crb.ranges import TemporalConstraint, Criteria
from cohort.crb.ranges import TemporalConstraint
from cohort.crb.source_population import SourcePopulation


@dataclass
class FhirRequest:
    cohort_uuid: str | None = None
    cohort_name: str | None = None
    source_population: SourcePopulation | None = None
    type: CriteriaType | None = None
    request: Criteria | None = None
    temporal_constraints: list[TemporalConstraint] = field(default_factory=list)
class FhirRequest(BaseModel):
    cohort_uuid: str = Field(None)
    cohort_name: str = Field(None)
    source_population: SourcePopulation = Field(alias="sourcePopulation")
    criteria_type: CriteriaType = Field(None, alias="_type")
    request: Criteria = Field(None)
    temporal_constraints: list[TemporalConstraint] = Field(default_factory=list)

