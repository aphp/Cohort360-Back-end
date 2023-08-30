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
