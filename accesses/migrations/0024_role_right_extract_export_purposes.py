from django.db import migrations, models
from django.db.models import Q

RIGHT_NAME = "right_extract_export_purposes"


def load_right_extract_export_purposes(apps, schema_editor):
    Right = apps.get_model("accesses", "Right")
    Role = apps.get_model("accesses", "Role")
    Right.objects.get_or_create(
        name=RIGHT_NAME,
        defaults={
            "label": "Extraire les motivations des exports locaux",
            "category": "Exports Jupyter",
            "is_global": True,
        },
    )
    # Granted to the roles that already have access to the list of transfer requests
    Role.objects.filter(Q(right_export_jupyter_nominative=True) | Q(right_export_jupyter_pseudonymized=True)).update(**{RIGHT_NAME: True})


def remove_right_extract_export_purposes(apps, schema_editor):
    Right = apps.get_model("accesses", "Right")
    Right.objects.filter(name=RIGHT_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accesses", "0023_load_right_read_logs"),
    ]

    operations = [
        migrations.AddField(
            model_name="role",
            name=RIGHT_NAME,
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(code=load_right_extract_export_purposes, reverse_code=remove_right_extract_export_purposes),
    ]
