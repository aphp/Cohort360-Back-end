# Generated by Django 4.1.4 on 2023-02-07 10:46

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accesses", "0026_caresite_concept_provider_alter_access_perimeter"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="provider_id",
            field=models.TextField(blank=True, null=True),
        ),
    ]
