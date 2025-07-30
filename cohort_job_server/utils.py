from admin_cohort.services.auth import auth_service
from cohort_job_server.apps import CohortJobServerConfig


JOB_STATUS = "request_job_status"
GROUP_ID = "group.id"
GROUP_COUNT = "group.count"
COUNT = "count"
MAXIMUM = "maximum"
MINIMUM = "minimum"
ERR_MESSAGE = "message"
EXTRA = "extra"


def allow_request_during_maintenance(request):
    applicative_tokens = CohortJobServerConfig.APPLICATIVE_USERS_TOKENS.keys()
    auth_token = auth_service.get_token_from_headers(request)[0]
    return auth_token in applicative_tokens