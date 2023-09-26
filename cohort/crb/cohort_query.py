from pydantic import BaseModel, Field

from cohort.crb.criteria import Criteria
from cohort.crb.enums import CriteriaType
from cohort.crb.ranges import TemporalConstraint
from cohort.crb.source_population import SourcePopulation


class CohortQuery(BaseModel):
    cohort_uuid: str = Field(None)
    cohort_name: str = Field(None)
    source_population: SourcePopulation = Field(alias="sourcePopulation")
    criteria_type: CriteriaType = Field(None, alias="_type")
    request: Criteria = Field(None)
    temporal_constraints: list[TemporalConstraint] = Field(default_factory=list)
