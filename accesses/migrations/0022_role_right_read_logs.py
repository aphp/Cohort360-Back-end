from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accesses", "0021_remove_role_right_read_practitioner_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="role",
            name="right_read_logs",
            field=models.BooleanField(default=False),
        ),
    ]
