from django.conf import settings
from rest_framework.request import Request

from cohort_job_server.permissions import SJSorETLCallbackPermission
from cohort_job_server.sjs_api import SJSRequester


class BaseCohortOperator:

    def __init__(self):
        self.sjs_requester = SJSRequester()
        self.applicative_users = [settings.SJS_USERNAME]

    def get_special_permissions(self, request: Request):
        if request.user.is_authenticated and request.user.username in self.applicative_users:
            return [SJSorETLCallbackPermission()]
