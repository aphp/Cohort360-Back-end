from celery import shared_task

from admin_cohort import celery_app
from admin_cohort.services.maintenance import MaintenanceService, maintenance_phase_to_info, WSMaintenanceInfo


@celery_app.task()
def maintenance_notifier_checker():
    event_to_start, event_to_end = MaintenanceService.get_maintenance_with_event()
    for event in event_to_start:
        maintenance_notifier.s(maintenance_phase_to_info(event).model_dump()).apply_async(eta=event.start_datetime)
    for event in event_to_end:
        maintenance_notifier.s(maintenance_phase_to_info(event).model_dump()).apply_async(eta=event.end_datetime)
    current_maintenance = MaintenanceService.get_current_maintenance()
    if current_maintenance:
        maintenance_notifier.s(maintenance_phase_to_info(current_maintenance).model_dump()).apply_async()


@shared_task
def maintenance_notifier(info: dict):
    maintenance_info = WSMaintenanceInfo.model_validate(info)
    MaintenanceService.send_maintenance_notification(maintenance_info)