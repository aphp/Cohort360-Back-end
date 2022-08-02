from django.http import JsonResponse
from rest_framework.permissions import SAFE_METHODS
from rest_framework.status import HTTP_503_SERVICE_UNAVAILABLE

from admin_cohort.models import get_next_maintenance


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith('/accounts/') \
                and not request.path.startswith('/maintenances/')\
                and request.method not in SAFE_METHODS:
            m = get_next_maintenance()
            if m is None or not m.active:
                return self.get_response(request)

            return JsonResponse(
                data=dict(
                    message=f"Le serveur est en maintenance jusqu'au "
                            f"{m.end_datetime.strftime('%d/%m/%Y, %H:%M:%S')}. "
                            f"La cause étant : {m.subject}",
                    maintenance_start=m.start_datetime,
                    maintenance_end=m.end_datetime,
                    active=True
                ),
                status=HTTP_503_SERVICE_UNAVAILABLE)

        return self.get_response(request)
