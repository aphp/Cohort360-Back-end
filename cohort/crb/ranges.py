from dataclasses import dataclass

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
    time_delay_min: str
    time_delay_max: str
    same_encounter: bool
    same_day: bool


class TemporalConstraintDuration:
    years: int
    months: int
    days: int
    hours: int
    minutes: int
    seconds: int


@dataclass
class TemporalConstraint:
    id_list: list
    constraint_type: str
    date_preference: list
    time_relation_min_duration: TemporalConstraintDuration
    timeRelationMaxDuration: TemporalConstraintDuration
    occurrence_choices: list
    dates_are_not_null: list
    filtered_criteria_id: list


@dataclass
class Criteria:
    criteria_type: CriteriaType
    _id: int
    is_inclusive: bool
    resource_type: ResourceType
    filter_solr: str
    filter_fhir: str
    patient_age: PatientAge
    criteria: list['Criteria']
    occurrence: Occurrence
    date_range: DateRange
    date_range_list: list[DateRange]
    encounter_date_range: DateRange
    temporal_constraints: list[TemporalConstraint]

    def add_criteria(self, obj) -> str | None:
        if self.filter_fhir is None:
            return
        return self.filter_fhir if obj is None else f"{obj}&{self.filter_fhir}"
