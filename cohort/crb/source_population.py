from dataclasses import dataclass


@dataclass
class SourcePopulation:
    care_site_cohort_list: list[int]

    def format_to_fhir(self) -> str:
        if not self.care_site_cohort_list:
            return ""
        return "_list=" + ",".join(map(str, self.care_site_cohort_list))
