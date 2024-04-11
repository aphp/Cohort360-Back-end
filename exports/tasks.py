import logging

from celery import shared_task

from admin_cohort.celery import celery_app
from admin_cohort.tools.celery_periodic_task_helper import ensure_single_task
from exports.models import ExportRequest, Export
from exports.services.export_operators import ExportManager, ExportCleaner

_logger = logging.getLogger('django.request')


@shared_task
def launch_export_task(export_id: str, export_model: ExportRequest | Export):
    ExportManager().handle_export(export_id=export_id, export_model=export_model)


@celery_app.task()
@ensure_single_task("delete_exported_files")
def delete_exported_files():
    ExportCleaner().delete_exported_files()
