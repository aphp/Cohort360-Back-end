from typing import Union

import environ
from django.utils import timezone
from rest_framework.permissions import SAFE_METHODS

from admin_cohort.models import MaintenancePhase
from admin_cohort.services.auth import auth_service

env = environ.Env()

ETL_TOKEN = env("ETL_TOKEN")
SJS_TOKEN = env("SJS_TOKEN")


class MaintenanceService:
    @staticmethod
    def get_next_maintenance() -> Union[MaintenancePhase, None]:
        now = timezone.now()
        current = MaintenancePhase.objects.filter(start_datetime__lte=now, end_datetime__gte=now)\
                                          .order_by('-end_datetime')\
                                          .first()
        if current:
            return current
        next_maintenance = MaintenancePhase.objects.filter(start_datetime__gte=now)\
                                                   .order_by('start_datetime')\
                                                   .first()
        return next_maintenance

    @staticmethod
    def is_allowed_request(request):
        auth_token = auth_service.get_token_from_headers(request)[0]
        is_sjs_etl_callback = auth_token in (SJS_TOKEN, ETL_TOKEN)
        return request.method in SAFE_METHODS or \
            request.path.startswith('/auth/') or \
            request.path.startswith('/maintenances/') or \
            is_sjs_etl_callback


maintenance_service = MaintenanceService()
