import os

from django.http import JsonResponse
from rest_framework.permissions import SAFE_METHODS
from rest_framework.status import HTTP_503_SERVICE_UNAVAILABLE

from admin_cohort.auth.auth_utils import get_token_from_headers
from admin_cohort.models import get_next_maintenance

env = os.environ
SJS_TOKEN = env.get("SJS_TOKEN")
ETL_TOKEN = env.get("ETL_TOKEN")


def is_allowed_request(request):
    auth_token = get_token_from_headers(request)[0]
    is_sjs_etl_callback = auth_token in (SJS_TOKEN, ETL_TOKEN)
    return request.method in SAFE_METHODS or \
        request.path.startswith('/accounts/') or \
        request.path.startswith('/maintenances/') or \
        is_sjs_etl_callback


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        maintenance = get_next_maintenance()
        if maintenance and maintenance.active:
            if is_allowed_request(request):
                return self.get_response(request)
            maintenance_data = dict(message=f"Le serveur est en maintenance jusqu'au "
                                            f"{maintenance.end_datetime.strftime('%d/%m/%Y, %H:%M:%S')} en raison de: {maintenance.subject}",
                                    maintenance_start=maintenance.start_datetime,
                                    maintenance_end=maintenance.end_datetime,
                                    active=True)
            return JsonResponse(data=maintenance_data, status=HTTP_503_SERVICE_UNAVAILABLE)

        return self.get_response(request)
