from rest_framework.request import Request

from cohort_job_server.apps import CohortJobServerConfig
from cohort_job_server.permissions import QueryExecutororETLCallbackPermission
from cohort_job_server.query_executor_api import QueryExecutorRequester


class BaseCohortOperator:

    def __init__(self):
        self.query_executor_requester = QueryExecutorRequester()
        self.applicative_users = CohortJobServerConfig.APPLICATIVE_USERS

    def get_special_permissions(self, request: Request):
        if request.user.is_authenticated and request.user.username in self.applicative_users:
            return [QueryExecutororETLCallbackPermission()]
