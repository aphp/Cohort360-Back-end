from pydantic import BaseModel, Field

from cohort.crb.enums import ResourceType
from cohort.crb.exceptions import FhirException


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
