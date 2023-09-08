from dataclasses import dataclass, field

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
    criteria_type: CriteriaType = None
    _id: int = None
    is_inclusive: bool = None
    resource_type: ResourceType = None
    filter_solr: str = None
    filter_fhir: str = None
    patient_age: PatientAge = None
    criteria: list['Criteria'] = field(default_factory=list)
    occurrence: Occurrence = None
    date_range: DateRange = None
    date_range_list: list[DateRange] = field(default_factory=list)
    encounter_date_range: DateRange = None
    temporal_constraints: list[TemporalConstraint] = field(default_factory=list)

    def add_criteria(self, obj) -> str | None:
        if self.filter_fhir is None:
            return
        return self.filter_fhir if obj is None else f"{obj}&{self.filter_fhir}"
