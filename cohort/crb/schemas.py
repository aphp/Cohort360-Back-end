from dataclasses import dataclass
from dataclasses import field
from typing import Optional

from pydantic import BaseModel, Field

from cohort.crb.enums import CriteriaType, ResourceType, Mode
from cohort.crb.exceptions import FhirException


class PatientAge(BaseModel):
    min_age: str = Field(alias='minAge')
    max_age: str = Field(alias='maxAge')
    date_is_not_null: bool = Field(alias='dateIsNotNull')
    date_preference: list[str] = Field(alias='datePreference')


class DateRange(BaseModel):
    min_date: str = Field(alias='minDate')
    max_date: str = Field(alias='maxDate')
    date_preference: list[str] = Field(alias='datePreference')
    date_is_not_null: bool = Field(alias='dateIsNotNull')


class Occurrence(BaseModel):
    n: int = Field(alias='n')
    operator: str = Field(alias='operator')
    time_delay_min: str = Field(default=None, alias='timeDelayMin')
    time_delay_max: str = Field(default=None, alias='timeDelayMax')
    same_encounter: bool = Field(default=None, alias='sameEncounter')
    same_day: bool = Field(default=None, alias='sameDay')


class TemporalConstraintDuration(BaseModel):
    years: int = Field(...)
    months: int = Field(...)
    days: int = Field(...)
    hours: int = Field(...)
    minutes: int = Field(...)
    seconds: int = Field(...)


class TemporalConstraint(BaseModel):
    id_list: list = Field(default=None, alias="idList")
    constraint_type: str = Field(default=None, alias="constraintType")
    date_preference: list = Field(default=None, alias="datePreferenceList")
    time_relation_min_duration: TemporalConstraintDuration = Field(default=None, alias="timeRelationMinDuration")
    timeRelationMaxDuration: TemporalConstraintDuration = Field(default=None, alias="timeRelationMaxDuration")
    occurrence_choices: list = Field(default=None, alias="occurrenceChoiceList")
    dates_are_not_null: list = Field(default=None, alias="dateIsNotNullList")
    filtered_criteria_id: list = Field(default=None, alias="filteredCriteriaIdList")


class SourcePopulation(BaseModel):
    care_site_cohort_list: list[int] = Field(default_factory=list, alias="caresiteCohortList")

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
    cohort_uuid: str = Field(None, alias='cohortUuid')
    cohort_name: str = Field(None, alias='cohortName')
    source_population: SourcePopulation = Field(alias="sourcePopulation")
    criteria_type: CriteriaType = Field(None, alias="_type")
    criteria: Criteria = Field(None, alias="request")
    temporal_constraints: list[TemporalConstraint] = Field(default_factory=list, alias='temporalConstraints')


@dataclass
class SparkJobObject:
    cohort_definition_name: str
    cohort_definition_syntax: CohortQuery
    mode: Mode
    owner_entity_id: str


class FhirParameter(BaseModel):
    name: str = Field(...)
    value: str = Field(alias="valueString")


class FhirParameters(BaseModel):
    resource: ResourceType = Field(alias="resourceType")
    params: list[FhirParameter] = Field(default_factory=list, alias="parameter")

    def to_dict(self):
        if not self.params:
            raise FhirException(f"FhirParameters must have at least one parameter, got {self}")
        return {
            "collection": self.extract_parameters("collection"),
            "fq": self.extract_parameters("fq")
        }

    def extract_parameters(self, param_name: str) -> str:
        lst = [param.value for param in self.params if param.name == param_name]
        return lst[0] if lst else None
