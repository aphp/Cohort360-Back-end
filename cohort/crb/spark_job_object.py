from dataclasses import dataclass

from cohort.crb.enums import Mode
from cohort.crb.fhir_request import FhirRequest


@dataclass
class SparkJobObject:
    cohort_definition_name: str
    cohort_definition_syntax: FhirRequest
    mode: Mode
    owner_entity_id: str

