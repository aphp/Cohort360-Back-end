from enum import Enum
from typing import List

from django.db import migrations

from cohort.models import CohortResult, DatedMeasure


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


class OldJobStatus(str, Enum):
    killed = "killed"
    finished = "finished"
    running = "running"
    started = "started"
    error = "error"
    unknown = "unknown"
    pending = "pending"


def update_dm_status(apps, schema_editor):
    MyDatedMeasure = apps.get_model('cohort', 'DatedMeasure')
    db_alias = schema_editor.connection.alias

    old_to_new = {
        OldJobStatus.killed: NewJobStatus.cancelled,
        OldJobStatus.finished: NewJobStatus.finished,
        OldJobStatus.running: NewJobStatus.started,
        OldJobStatus.started: NewJobStatus.started,
        OldJobStatus.error: NewJobStatus.failed,
        OldJobStatus.unknown: NewJobStatus.unknown,
        OldJobStatus.pending: NewJobStatus.pending
    }

    dms: List[DatedMeasure] = list(
        MyDatedMeasure.objects.using(db_alias).all())
    for dm in dms:
        dm.new_request_job_status = old_to_new.get(dm.request_job_status,
                                                   NewJobStatus.unknown)
    MyDatedMeasure.objects.using(db_alias)\
        .bulk_update(dms, ['new_request_job_status'])


def update_cr_status(apps, schema_editor):
    MyCohortResult = apps.get_model('cohort', 'CohortResult')
    db_alias = schema_editor.connection.alias

    old_to_new = {
        'new': NewJobStatus.new,
        'validated': NewJobStatus.validated,
        'done': NewJobStatus.finished,
        'failed': NewJobStatus.failed,
        'denied': NewJobStatus.denied,
        'running': NewJobStatus.started,
        'canceled': NewJobStatus.cancelled,
        'to delete': NewJobStatus.unknown,
        'deleted': NewJobStatus.cleaned
    }

    crs: List[CohortResult] = list(
        MyCohortResult.objects.using(db_alias).all())
    for cr in crs:
        cr.new_request_job_status = old_to_new.get(cr.request_job_status,
                                                   NewJobStatus.unknown)
    MyCohortResult.objects.using(db_alias)\
        .bulk_update(crs, ['new_request_job_status'])


class Migration(migrations.Migration):

    dependencies = [
        ('cohort', '0010_auto_20220428_1314'),
    ]

    operations = [
        migrations.RunPython(update_dm_status),
        migrations.RunPython(update_cr_status),
    ]
