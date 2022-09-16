# Generated by Django 2.2.16 on 2022-04-05 12:13
from enum import Enum
from typing import List

from django.db import migrations

from exports.models import ExportRequest


class NewJobStatus(str, Enum):
    new = "new"
    denied = "denied"
    validated = "validated"
    pending = "pending"
    started = "started"
    failed = "failed"
    cancelled = "cancelled"
    finished = "finished"
    cleaned = "cleaned"
    unknown = "unknown"


def update_status(apps, schema_editor):
    MyExportRequest = apps.get_model('exports', 'ExportRequest')
    db_alias = schema_editor.connection.alias

    old_to_new = {
        'new': NewJobStatus.new.value,
        'validated': NewJobStatus.validated.value,
        'done': NewJobStatus.finished.value,
        'failed': NewJobStatus.failed.value,
        'denied': NewJobStatus.denied.value,
        'running': NewJobStatus.started.value,
        'canceled': NewJobStatus.cancelled.value,
        'to delete': NewJobStatus.unknown.value,
        'deleted': NewJobStatus.cleaned.value
    }

    ers: List[ExportRequest] = list(
        MyExportRequest.objects.using(db_alias).all())
    to_update = list()
    for er in ers:
        if not er.new_request_job_status:
            er.new_request_job_status = old_to_new.get(
                er.status, NewJobStatus.unknown.value)
            er.status = None
            to_update.append(er)
    MyExportRequest.objects.using(db_alias)\
        .bulk_update(to_update, ['new_request_job_status', 'status'])


def rollback_status(apps, schema_editor):
    MyExportRequest = apps.get_model('exports', 'ExportRequest')
    db_alias = schema_editor.connection.alias

    new_to_old = {
        NewJobStatus.new.value: 'new',
        NewJobStatus.validated.value: 'validated',
        NewJobStatus.finished.value: 'done',
        NewJobStatus.failed.value: 'failed',
        NewJobStatus.denied.value: 'denied',
        NewJobStatus.started.value: 'running',
        NewJobStatus.cancelled.value: 'canceled',
        NewJobStatus.unknown.value: 'to delete',
        NewJobStatus.cleaned.value: 'deleted'
    }

    ers: List[ExportRequest] = list(
        MyExportRequest.objects.using(db_alias).all())
    to_update = list()
    for er in ers:
        if not er.status:
            er.status = new_to_old.get(er.new_request_job_status,
                                       NewJobStatus.unknown.value)
            er.new_request_job_status = None
            to_update.append(er)
    MyExportRequest.objects.using(db_alias)\
        .bulk_update(to_update, ['status', 'new_request_job_status'])


class Migration(migrations.Migration):

    dependencies = [
        ('exports', '0011_delete_cohortdefinition'),
    ]

    operations = [
        migrations.RunPython(update_status, reverse_code=rollback_status),
    ]
