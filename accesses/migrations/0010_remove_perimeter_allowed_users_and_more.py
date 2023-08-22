# Generated by Django 4.1.7 on 2023-08-22 13:13

from django.db import migrations, models
from django.db.models import Count

from accesses.models.tools import q_is_valid_access


def compute_allowed_users(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    access_model = apps.get_model('accesses', 'Access')
    perimeter_model = apps.get_model('accesses', 'Perimeter')

    perimeters_count = access_model.objects.using(db_alias).filter(q_is_valid_access()) \
                                                           .distinct("profile__user_id") \
                                                           .values("perimeter_id") \
                                                           .annotate(count=Count("perimeter_id"))
    for p in perimeters_count:
        try:
            perimeter = perimeter_model.objects.get(pk=p.get("perimeter_id"))
            perimeter.count_allowed_users = p.get("count")
            perimeter.save()
        except perimeter_model.DoesNotExist:
            continue


def compute_allowed_users_from_inferior_levels(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    perimeter_model = apps.get_model('accesses', 'Perimeter')


def compute_allowed_users_from_above_levels(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    perimeter_model = apps.get_model('accesses', 'Perimeter')


class Migration(migrations.Migration):

    dependencies = [
        ('accesses', '0009_compute_allowed_users_above_levels'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='perimeter',
            name='allowed_users',
        ),
        migrations.RemoveField(
            model_name='perimeter',
            name='allowed_users_above_levels',
        ),
        migrations.RemoveField(
            model_name='perimeter',
            name='allowed_users_inferior_levels',
        ),
        migrations.AddField(
            model_name='perimeter',
            name='count_allowed_users',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
        migrations.AddField(
            model_name='perimeter',
            name='count_allowed_users_above_levels',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
        migrations.AddField(
            model_name='perimeter',
            name='count_allowed_users_inferior_levels',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
        # migrations.RunPython(code=compute_allowed_users),
        # migrations.RunPython(code=compute_allowed_users_from_inferior_levels),
        # migrations.RunPython(code=compute_allowed_users_from_above_levels),
    ]
