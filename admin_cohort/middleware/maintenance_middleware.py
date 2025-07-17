from django.http import JsonResponse
from rest_framework.status import HTTP_503_SERVICE_UNAVAILABLE

from admin_cohort.services.maintenance import maintenance_service


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        maintenance = maintenance_service.get_next_maintenance()
        if maintenance and maintenance.active:
            if maintenance_service.is_allowed_request(request):
                return self.get_response(request)
            data = {"message": f"The server is unavailable for maintenance up to {maintenance.end_datetime.strftime('%d/%m/%Y, %H:%M:%S')} "
                               f"for the following reason: {maintenance.message}",
                    "maintenance_start": maintenance.start_datetime,
                    "maintenance_end": maintenance.end_datetime,
                    "active": True
                    }
            return JsonResponse(data=data, status=HTTP_503_SERVICE_UNAVAILABLE)
        return self.get_response(request)
