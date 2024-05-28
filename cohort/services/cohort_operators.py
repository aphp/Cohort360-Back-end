from cohort.models import CohortResult, DatedMeasure, FeasibilityStudy


class DefaultCohortCounter:

    @staticmethod
    def launch_count(dm: DatedMeasure, request) -> None:
        raise NotImplementedError()

    @staticmethod
    def launch_global_count(cohort: CohortResult, request) -> None:
        raise NotImplementedError()

    @staticmethod
    def launch_feasibility_study_count(fs: FeasibilityStudy, request) -> None:
        raise NotImplementedError()


class DefaultCohortCreator:

    @staticmethod
    def launch_cohort_creation(cohort: CohortResult, request) -> None:
        raise NotImplementedError()

    @staticmethod
    def handle_patch_data(cohort: CohortResult, data: dict) -> None:
        raise NotImplementedError()
