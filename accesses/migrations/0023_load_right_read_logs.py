from django.db import migrations


def load_right_read_logs(apps, schema_editor):
    Right = apps.get_model("accesses", "Right")
    Right.objects.get_or_create(
        name="right_read_logs",
        defaults={
            "label": "Consulter les logs",
            "category": "Logs",
            "is_global": True,
        },
    )


def remove_right_read_logs(apps, schema_editor):
    Right = apps.get_model("accesses", "Right")
    Right.objects.filter(name="right_read_logs").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accesses", "0022_role_right_read_logs"),
    ]

    operations = [
        migrations.RunPython(code=load_right_read_logs, reverse_code=remove_right_read_logs),
    ]
