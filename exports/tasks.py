import logging

from celery import shared_task

from admin_cohort.celery import celery_app
from exporters.exporters.base_exporter import BaseExporter
from exports.models import Export
from exports.services.export_operators import ExportCleaner

_logger = logging.getLogger('django.request')



@celery_app.task()
def delete_exported_files():
    ExportCleaner().delete_exported_files()


@shared_task
def get_logs(export_id: str) -> dict:
    export = Export.objects.get(pk=export_id)
    return BaseExporter().export_api.get_export_logs(job_id=export.request_job_id)