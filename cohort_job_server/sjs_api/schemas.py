from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from cohort_job_server.sjs_api.enums import CriteriaType, ResourceType, Mode
from cohort_job_server.sjs_api.exceptions import FhirException


class PatientAge(BaseModel):
    min_age: Optional[str] = Field(default=None, alias='minAge')
    max_age: Optional[str] = Field(default=None, alias='maxAge')
    date_is_not_null: Optional[bool] = Field(default=None, alias='dateIsNotNull')
    date_preference: Optional[list[str]] = Field(default=None, alias='datePreference')


class DateRange(BaseModel):
    min_date: Optional[str] = Field(default=None, alias='minDate')
    max_date: Optional[str] = Field(default=None, alias='maxDate')
    date_preference: Optional[list[str]] = Field(default=None, alias='datePreference')
    date_is_not_null: Optional[bool] = Field(default=None, alias='dateIsNotNull')


class Occurrence(BaseModel):
    n: int = Field(alias='n')
    operator: str = Field(alias='operator')
    time_delay_min: str = Field(default=None, alias='timeDelayMin')
    time_delay_max: str = Field(default=None, alias='timeDelayMax')
    same_encounter: bool = Field(default=None, alias='sameEncounter')
    same_day: bool = Field(default=None, alias='sameDay')


class NAmongMOption(BaseModel):
    n: int = Field(alias='n')
    operator: str = Field(alias='operator')


class TemporalConstraintDuration(BaseModel):
    years: Optional[int] = Field(default=None)
    months: Optional[int] = Field(default=None)
    days: Optional[int] = Field(default=None)
    hours: Optional[int] = Field(default=None)
    minutes: Optional[int] = Field(default=None)
    seconds: Optional[int] = Field(default=None)


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
    criteria: list['Criteria'] = Field(default_factory=list)
    occurrence: Occurrence = Field(None, alias="occurrence")
    date_range: DateRange = Field(None, alias="dateRange")
    date_range_list: list[DateRange] = Field(default_factory=list, alias="dateRangeList")
    encounter_date_range: DateRange = Field(None, alias="encounterDateRange")
    temporal_constraints: list[TemporalConstraint] = Field(default_factory=list, alias="temporalConstraints")
    n_among_m_options: NAmongMOption = Field(None, alias="nAmongMOptions")

    def add_criteria(self, obj) -> Optional[str]:
        if self.filter_fhir is None:
            return None
        return self.filter_fhir if obj is None else f"{obj}&{self.filter_fhir}"


class CohortQuery(BaseModel):
    instance_id: Optional[UUID] = Field(None, alias='instance_id')
    cohort_name: str = Field(None, alias='cohortName')
    source_population: SourcePopulation = Field(None, alias="sourcePopulation")
    resource_type: ResourceType = Field(None, alias="resourceType")
    criteria_type: CriteriaType = Field(None, alias="_type")
    criteria: Criteria = Field(None, alias="request")
    temporal_constraints: list[TemporalConstraint] = Field(default_factory=list, alias='temporalConstraints')


class ModeOptions(BaseModel):
    sampling: Optional[float] = Field(None, alias='sampling')
    details: Optional[str] = Field(None, alias='details')


@dataclass
class SparkJobObject:
    cohort_definition_name: str
    cohort_definition_syntax: CohortQuery
    mode: Mode
    owner_entity_id: str
    callbackPath: Optional[str] = Field(None, alias='callbackPath')
    existingCohortId: Optional[int] = Field(None, alias='existingCohortId')
    modeOptions: Optional[ModeOptions] = Field(None, alias='modeOptions')


class FhirParameter(BaseModel):
    name: str = Field(...)
    value: str = Field(alias="valueString")


class FhirParameters(BaseModel):
    resource: str = Field(alias="resourceType")
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
