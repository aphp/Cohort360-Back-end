# Generated by Django 4.2.11 on 2024-05-28 15:31
import logging

from django.db import migrations, models
from accesses.serializers import RightSerializer


_logger = logging.getLogger('info')


def load_new_right(apps, schema_editor):
    right_data = {"label": "Chercher les patients sans limite de périmètre (PP)",
                  "name": "right_search_patients_unlimited",
                  "category": "Recherche de Patients",
                  "is_global": True}
    right_serializer = RightSerializer(data=right_data, many=False)
    if right_serializer.is_valid():
        right_serializer.save()
    else:
        _logger.error(f"Error on loading right: {right_serializer.errors}")
        return


class Migration(migrations.Migration):

    dependencies = [
        ('accesses', '0014_rightcategory_right'),
    ]

    operations = [
        migrations.AddField(
            model_name='role',
            name='right_search_patients_unlimited',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(code=load_new_right)
    ]
