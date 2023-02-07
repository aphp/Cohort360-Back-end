# Generated by Django 4.1.4 on 2023-02-07 10:46

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("admin_cohort", "0011_remove_schemas"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="provider_id",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.RunSQL(
            "UPDATE user "
            "SET provider_id=provider_username"
        )
    ]
