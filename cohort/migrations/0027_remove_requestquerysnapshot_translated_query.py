import json
import re

from django.db import migrations

REFRESH_TASK = "cohort.tasks.refresh_count_request"
UUID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
LAST_QUOTED_PATTERN = re.compile(r"""['"]([\w.]+)['"]\s*\]\s*$""")


def drop_translated_query_from_refresh_tasks(apps, schema_editor):
    # Old args: str([UUID(dm_id), translated_query, cohort_counter_cls]), a Python repr that celery beat
    # can't parse as JSON, so it disabled these tasks. New args: JSON [dm_id, cohort_counter_cls], re-enabled.
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    for task in PeriodicTask.objects.filter(task=REFRESH_TASK):
        dm_id = UUID_PATTERN.search(task.args or "")
        counter_cls = LAST_QUOTED_PATTERN.search(task.args or "")
        if dm_id and counter_cls:
            task.args = json.dumps([dm_id.group(0), counter_cls.group(1)])
            task.enabled = True
            task.save(update_fields=["args", "enabled"])


class Migration(migrations.Migration):
    dependencies = [
        ("cohort", "0026_fhirfilter_only_pdf_available"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(drop_translated_query_from_refresh_tasks, migrations.RunPython.noop),
        migrations.RemoveField(model_name="requestquerysnapshot", name="translated_query"),
    ]
