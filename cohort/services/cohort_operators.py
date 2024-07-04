from typing import Tuple

from rest_framework.request import Request

from admin_cohort.types import JobStatus
from cohort.permissions import IsOwnerPermission


class DefaultCohortOperator:

    def __init__(self):
        self.applicative_users = []

    def get_special_permissions(self, request: Request):
        if request.user.username not in self.applicative_users:
            return [IsOwnerPermission()]


class DefaultCohortCounter(DefaultCohortOperator):

    @staticmethod
    def launch_dated_measure_count(*args, **kwargs) -> None:
        """
        request an API to execute the count query
        @return: None
        """
        raise NotImplementedError()

    @staticmethod
    def launch_feasibility_study_count(*args, **kwargs) -> bool:
        """
        request an API to execute the count query
        @return: bool if the task ended successfully
        """
        return True

    @staticmethod
    def cancel_job(*args, **kwargs) -> JobStatus:
        """
        request an API to cancel a counting job
        @return: JobStatus
        """
        return JobStatus.cancelled

    @staticmethod
    def handle_patch_dated_measure(*args, **kwargs) -> None:
        """
        specific processing if necessary
        @return: None
        """
        raise NotImplementedError()

    @staticmethod
    def handle_patch_feasibility_study(*args, **kwargs) -> Tuple[JobStatus, dict]:
        """
        specific processing if necessary
        @return: new status of the count job and dict for detailed count
        """
        return JobStatus.finished, {}


class DefaultCohortCreator(DefaultCohortOperator):

    @staticmethod
    def launch_cohort_creation(*args, **kwargs) -> None:
        """
        request an API to create a cohort
        @return: None
        """
        raise NotImplementedError()

    @staticmethod
    def handle_patch_cohort(*args, **kwargs) -> None:
        """
        specific processing if necessary
        @return: None
        """
        raise NotImplementedError()

    @staticmethod
    def handle_cohort_post_update(*args, **kwargs) -> None:
        """
        specific processing if necessary
        @return: None
        """
        raise NotImplementedError()
