import logging
from datetime import timedelta
from typing import Union, Optional

import dateutil.parser
import environ
from django.utils import timezone
from pydantic import BaseModel
from rest_framework.permissions import SAFE_METHODS

from admin_cohort import settings
from admin_cohort.models import MaintenancePhase
from admin_cohort.services.auth import auth_service
from admin_cohort.services.ws_event_manager import WebSocketMessage, WebsocketManager, WebSocketMessageType

_logger = logging.getLogger("info")

env = environ.Env()

ETL_TOKEN = env("ETL_TOKEN")
SJS_TOKEN = env("SJS_TOKEN")


class WSMaintenanceInfo(BaseModel):
    subject: Optional[str]
    maintenance_start: str
    maintenance_end: str
    active: bool
    type: str
    message: Optional[str]


class WSMaintenance(WebSocketMessage):
    info: WSMaintenanceInfo


def maintenance_phase_to_info(maintenance: MaintenancePhase) -> WSMaintenanceInfo:
    return WSMaintenanceInfo(
        subject=maintenance.subject,
        maintenance_start=maintenance.start_datetime.isoformat(),
        maintenance_end=maintenance.end_datetime.isoformat(),
        active=maintenance.active,
        type=maintenance.type,
        message=maintenance.message
    )


class MaintenanceService:

    @staticmethod
    def get_maintenance_with_event():
        now = timezone.now()
        # setting start time to 1 minute before now to avoid missing the event (sending twice the notification isn't really a problem)
        start_time = now - timedelta(minutes=1)
        end_time = now + timedelta(minutes=settings.MAINTENANCE_PERIODIC_SCHEDULING_MINUTES)
        event_to_start = MaintenancePhase.objects.filter(start_datetime__range=(start_time, end_time))
        event_to_end = MaintenancePhase.objects.filter(end_datetime__range=(start_time, end_time))
        return event_to_start, event_to_end

    @staticmethod
    def send_maintenance_notification(maintenance_info: WSMaintenanceInfo):
        now = timezone.now()
        start_time = dateutil.parser.parse(maintenance_info.maintenance_start)
        end_time = dateutil.parser.parse(maintenance_info.maintenance_end)
        maintenance_info.active = start_time < now < end_time
        logging.info(f"Sending maintenance notification: {maintenance_info}")
        WebsocketManager.send_to_client("__all__", WSMaintenance(type=WebSocketMessageType.MAINTENANCE, info=maintenance_info))

    @staticmethod
    def get_next_maintenance() -> Union[MaintenancePhase, None]:
        now = timezone.now()
        current = MaintenancePhase.objects.filter(start_datetime__lte=now, end_datetime__gte=now) \
            .order_by('-end_datetime') \
            .first()
        if current:
            return current
        next_maintenance = MaintenancePhase.objects.filter(start_datetime__gte=now) \
            .order_by('start_datetime') \
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
