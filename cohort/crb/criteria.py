import json
from dataclasses import field
from typing import Optional, List

from pydantic import BaseModel, Field

from cohort.crb.enums import CriteriaType, ResourceType
from cohort.crb.ranges import PatientAge, Occurrence, DateRange, TemporalConstraint


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
