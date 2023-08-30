from dataclasses import dataclass

from cohort.crb.enums import ResourceType


@dataclass
class FhirParameter:
    name: str
    value: str


@dataclass
class FhirParameters:
    resource: ResourceType
    params: list[FhirParameter]