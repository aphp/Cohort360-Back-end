from dataclasses import dataclass
from dataclasses import field
from typing import Optional

from pydantic import BaseModel, Field

from cohort.crb.enums import CriteriaType, ResourceType


@dataclass
class PatientAge:
    min_age: str
    max_age: str
    date_is_not_null: bool
    date_preference: list[str]


@dataclass
class DateRange:
    min_date: str
    maxDate: str
    date_preference: list[str]
    date_is_not_null: bool


@dataclass
class Occurrence:
    n: int
    operator: str
    time_delay_min: str = None
    time_delay_max: str = None
    same_encounter: bool = None
    same_day: bool = None


@dataclass
class TemporalConstraintDuration:
    years: int
    months: int
    days: int
    hours: int
    minutes: int
    seconds: int


@dataclass
class TemporalConstraint:
    id_list: list = None
    constraint_type: str = None
    date_preference: list = None
    time_relation_min_duration: TemporalConstraintDuration = None
    timeRelationMaxDuration: TemporalConstraintDuration = None
    occurrence_choices: list = None
    dates_are_not_null: list = None
    filtered_criteria_id: list = None


class SourcePopulation(BaseModel):
    care_site_cohort_list: list[int] = Field(default_factory=list, alias="careSiteCohortList")

    def format_to_fhir(self) -> str:
        if not self.care_site_cohort_list:
            return ""
        return "_list=" + ",".join(map(str, self.care_site_cohort_list))


class Criteria(BaseModel):
    # aliases are mainly converting camel case to snake case
    criteria_type: CriteriaType = Field(None, alias="_type")
    id: int = Field(None, alias="_id")
    is_inclusive: bool = Field(None, alias="isInclusive")
    resource_type: ResourceType = Field(None, alias="resourceType")
    filter_solr: str = Field(None, alias="filterSolr")
    filter_fhir: str = Field(None, alias="filterFhir")
    patient_age: PatientAge = Field(None, alias="patientAge")
    criteria: list['Criteria'] = field(default_factory=list)
    occurrence: Occurrence = Field(None, alias="occurrence")
    date_range: DateRange = Field(None, alias="dateRange")
    date_range_list: list[DateRange] = Field(default_factory=list, alias="dateRangeList")
    encounter_date_range: DateRange = Field(None, alias="encounterDateRange")
    temporal_constraints: list[TemporalConstraint] = Field(default_factory=list, alias="temporalConstraints")

    def add_criteria(self, obj) -> Optional[str]:
        if self.filter_fhir is None:
            return None
        return self.filter_fhir if obj is None else f"{obj}&{self.filter_fhir}"


class CohortQuery(BaseModel):
    cohort_uuid: str = Field(None)
    cohort_name: str = Field(None)
    source_population: SourcePopulation = Field(alias="sourcePopulation")
    criteria_type: CriteriaType = Field(None, alias="_type")
    request: Criteria = Field(None)
    temporal_constraints: list[TemporalConstraint] = Field(default_factory=list)
