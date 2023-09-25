from pydantic import Field, BaseModel


class SourcePopulation(BaseModel):
    care_site_cohort_list: list[int] = Field(default_factory=list, alias="careSiteCohortList")

    def format_to_fhir(self) -> str:
        if not self.care_site_cohort_list:
            return ""
        return "_list=" + ",".join(map(str, self.care_site_cohort_list))
