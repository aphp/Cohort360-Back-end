import logging
from functools import lru_cache

from celery import shared_task
from django.conf import settings

from exports.models import Export
from exports.emails import push_email_notification
from exporters.notifications import export_failed_notif_for_owner, export_failed_notif_for_admins, \
    EXPORT_RECEIVED_NOTIFICATIONS, EXPORT_SUCCEEDED_NOTIFICATIONS

_logger = logging.getLogger('django.request')


def get_export_by_id(export_id: str | int) -> Export:
    try:
        return Export.objects.get(pk=export_id)
    except Export.DoesNotExist:
        raise ValueError(f'No export matches the given ID : {export_id}')


@lru_cache(maxsize=None)
def get_cohort(export: Export):
    sample_table = export.export_tables.filter(cohort_result_source__isnull=False).first()
    return sample_table.cohort_result_source


def get_selected_tables(export: Export) -> str:
    return export.export_tables.values_list("name", flat=True)


@shared_task
def notify_export_received(export_id: str) -> None:
    export = get_export_by_id(export_id)
    export_type = export.output_format

    try:
        cohort = get_cohort(export=export)
        notification_data = {"recipient_name": export.owner.display_name,
                             "recipient_email": export.owner.email,
                             "retried": export.retried,
                             "cohort_id": cohort and cohort.group_id or None,
                             "cohort_name": cohort and cohort.name or None,
                             "selected_tables": get_selected_tables(export=export)
                             }
        push_email_notification(base_notification=EXPORT_RECEIVED_NOTIFICATIONS[export_type],
                                **notification_data)
    except Exception as e:
        _logger.error(f"Error sending export confirmation email - {e}")


@shared_task
def notify_export_succeeded(export_id: str) -> None:
    export = get_export_by_id(export_id)
    cohort = get_cohort(export=export)
    notification_data = {"recipient_name": export.owner.display_name,
                         "recipient_email": export.owner.email,
                         "export_request_id": export.pk,
                         "cohort_id": cohort and cohort.group_id or None,
                         "cohort_name": cohort and cohort.name or None,
                         "database_name": export.target_name,
                         "selected_tables": get_selected_tables(export=export)
                         }
    try:
        push_email_notification(base_notification=EXPORT_SUCCEEDED_NOTIFICATIONS.get(export.output_format),
                                **notification_data)
    except OSError:
        _logger.error(f"[Export {export.pk}] Error sending export success notification")
    else:
        export.is_user_notified = True
        export.save()


def notify_export_owner(export: Export, base_notification_data: dict) -> None:
    notification_data = {**base_notification_data,
                         "recipient_name": export.owner.display_name,
                         "recipient_email": export.owner.email
                         }
    try:
        push_email_notification(base_notification=export_failed_notif_for_owner, **notification_data)
    except OSError:
        _logger.error(f"[Export {export.pk}] Error sending export failure notification")
    else:
        export.is_user_notified = True
        export.save()


def notify_admins(export: Export, base_notification_data: dict) -> None:
    notification_data = {**base_notification_data,
                         "export_id": export.pk,
                         "export_date": export.created_at.isoformat(),
                         "job_id": export.request_job_id,
                         "job_duration": export.request_job_duration,
                         "host": settings.BACKEND_URL,
                         }
    try:
        push_email_notification(base_notification=export_failed_notif_for_admins, **notification_data)
    except OSError:
        _logger.error(f"[Export {export.pk}] Error sending export failure notification to admins")


@shared_task
def notify_export_failed(export_id: str, reason: str) -> None:
    _logger.info(f"[Export {export_id}] {reason}")
    export = get_export_by_id(export_id)
    cohort = get_cohort(export=export)
    base_notification_data = {"cohort_id": cohort and cohort.group_id or None,
                              "cohort_name": cohort and cohort.name or None,
                              "error_message": reason
                              }
    notify_export_owner(export, base_notification_data)
    notify_admins(export, base_notification_data)