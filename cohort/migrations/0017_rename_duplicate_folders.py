# Generated by Django 2.2.28 on 2022-11-02 07:55
import re

from django.conf import settings
from django.db import migrations
from django.db.models import Count


def rename_duplicate_folders(apps, schema_editor):
    folder_model = apps.get_model('cohort', 'Folder')
    db_alias = schema_editor.connection.alias

    duplicate_fodlers_data = folder_model.objects.using(db_alias).all().values("name", "owner_id")\
        .annotate(total=Count("name")).filter(total__gte=2)
    for item in duplicate_fodlers_data:
        folders_to_update = folder_model.objects.using(db_alias).filter(name=item["name"],
                                                                        owner__provider_username=item["owner_id"]).\
            order_by("created_at")
        for i, f in enumerate(folders_to_update[1:]):   # no need to update the first created folder
            f.name = f"{f.name} ({i+2})"
            f.save()


def rollback_duplicate_folders_names(apps, schema_editor):
    folder_model = apps.get_model('cohort', 'Folder')
    db_alias = schema_editor.connection.alias
    renamed_folders = folder_model.objects.using(db_alias).filter(name__regex=r'([A-Za-z0-9_]+) \(([0-9]+)\)$')
    for f in renamed_folders:
        f.name = re.split(r'\(\d+\)', f.name)[0].strip()
        f.save()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cohort', '0016_auto_20220916_1824'),
    ]

    operations = [
        migrations.RunPython(rename_duplicate_folders,
                             reverse_code=rollback_duplicate_folders_names),
    ]
