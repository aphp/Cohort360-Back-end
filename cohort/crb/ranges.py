from dataclasses import dataclass


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
