from cohort.models import DatedMeasure
from cohort.services.cohort_managers import CohortCounter


class DatedMeasureService:

    @staticmethod
    def process_dated_measure(dm: DatedMeasure, request) -> None:
        CohortCounter().handle_count(dm, request)

    @staticmethod
    def handle_patch_data(dm: DatedMeasure, data: dict) -> None:
        CohortCounter().handle_patch_dated_measure(dm, data)


dated_measure_service = DatedMeasureService()
