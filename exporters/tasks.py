import logging

from celery import shared_task

from admin_cohort.types import JobStatus
from exporters.enums import ExportTypes
from exports.models import Export, ExportRequest
from exports.emails import push_email_notification
from exporters.notifications import export_failed, \
    EXPORT_RECEIVED_NOTIFICATIONS, EXPORT_SUCCEEDED_NOTIFICATIONS

_logger = logging.getLogger('django.request')


def get_export_by_id(export_id: str | int) -> Export | ExportRequest:
    model = str(export_id).isnumeric() and ExportRequest or Export
    try:
        return model.objects.get(pk=export_id)
    except model.DoesNotExist:
        raise ValueError(f'No export matches the given ID : {export_id}')


def get_cohort_id(export: Export | ExportRequest) -> int | str:
    if isinstance(export, ExportRequest):
        return export.cohort_id
    if export.output_format == ExportTypes.CSV.value:
        return export.export_tables.first().cohort_result_source.fhir_group_id
    return '--'


def get_selected_tables(export: Export | ExportRequest) -> str:
    if isinstance(export, ExportRequest):
        return export.tables.values_list("omop_table_name", flat=True)
    return export.export_tables.values_list("name", flat=True)


@shared_task
def notify_export_received(export_id: str) -> None:
    export = get_export_by_id(export_id)
    export_type = export.output_format

    try:
        notification_data = dict(recipient_name=export.owner.display_name,
                                 recipient_email=export.owner.email,
                                 cohort_id=get_cohort_id(export=export),
                                 cohort_name=export.cohort_name,
                                 selected_tables=get_selected_tables(export=export))
        push_email_notification(base_notification=EXPORT_RECEIVED_NOTIFICATIONS[export_type],
                                **notification_data)
    except Exception as e:
        _logger.error(f"Error sending export confirmation email - {e}")


@shared_task
def notify_export_succeeded(export_id: str) -> None:
    export = get_export_by_id(export_id)
    notification_data = dict(recipient_name=export.owner.display_name,
                             recipient_email=export.owner.email,
                             export_request_id=export.pk,
                             cohort_id=get_cohort_id(export=export),
                             cohort_name=export.cohort_name,
                             database_name=export.target_name,
                             selected_tables=get_selected_tables(export=export))
    try:
        push_email_notification(base_notification=EXPORT_SUCCEEDED_NOTIFICATIONS.get(export.output_format),
                                **notification_data)
    except OSError:
        _logger.error(f"[ExportRequest: {export.pk}] Error sending export success notification")
    else:
        export.is_user_notified = True
        export.save()


@shared_task
def notify_export_failed(export_id: str, reason: str) -> None:
    export = get_export_by_id(export_id)
    _logger.error(f"[ExportTask] [ExportRequest: {export.pk}] {reason}")
    export.request_job_status = JobStatus.failed
    export.request_job_fail_msg = reason
    notification_data = dict(recipient_name=export.owner.display_name,
                             recipient_email=export.owner.email,
                             cohort_id=get_cohort_id(export=export),
                             cohort_name=export.cohort_name,
                             error_message=reason)
    try:
        push_email_notification(base_notification=export_failed, **notification_data)
    except OSError:
        _logger.error(f"[ExportRequest: {export.pk}] Error sending export failure notification")
    else:
        export.is_user_notified = True
    export.save()
