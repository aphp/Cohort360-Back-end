from typing import Tuple

from rest_framework.request import Request

from admin_cohort.types import JobStatus


class DefaultCohortOperator:

    def __init__(self):
        self.applicative_users = []

    def get_special_permissions(self, request: Request):
        return None


class DefaultCohortCounter(DefaultCohortOperator):

    @staticmethod
    def launch_count(*args, **kwargs) -> None:
        raise NotImplementedError()

    @staticmethod
    def launch_feasibility_study_count(*args, **kwargs) -> bool:
        raise NotImplementedError()

    @staticmethod
    def handle_patch_dated_measure(fs, data):
        raise NotImplementedError()

    @staticmethod
    def handle_patch_feasibility_study(fs, data) -> Tuple[JobStatus, dict]:
        return JobStatus.finished, {}


class DefaultCohortCreator(DefaultCohortOperator):

    @staticmethod
    def launch_cohort_creation(*args, **kwargs) -> None:
        raise NotImplementedError()

    @staticmethod
    def handle_patch_data(*args, **kwargs) -> None:
        raise NotImplementedError()

    @staticmethod
    def handle_cohort_post_update(*args, **kwargs) -> None:
        raise NotImplementedError()
