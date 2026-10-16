from django.db import migrations


def finish_long_pending_dated_measures(apps, schema_editor):
    # A count only went `long_pending` by copying its big cohort's status, while its value was already known
    DatedMeasure = apps.get_model("cohort", "DatedMeasure")
    DatedMeasure.objects.filter(request_job_status="long_pending", measure__isnull=False).update(request_job_status="finished")


class Migration(migrations.Migration):
    dependencies = [
        ("cohort", "0027_remove_requestquerysnapshot_translated_query"),
    ]

    operations = [
        migrations.RunPython(finish_long_pending_dated_measures, migrations.RunPython.noop),
    ]
