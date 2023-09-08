from dataclasses import dataclass

from cohort.crb.enums import ResourceType
from cohort.crb.exceptions import FhirException


@dataclass
class FhirParameter:
    name: str
    value: str


@dataclass
class FhirParameters:
    resource: ResourceType
    params: list[FhirParameter]

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
