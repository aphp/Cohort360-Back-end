# Generated by Django 4.1.7 on 2023-10-03 12:21

import django.contrib.postgres.fields
from django.db import migrations, models


def create_old_release_notes(apps, schema_editor):
    release_notes = []
    release_note_model = apps.get_model('admin_cohort', 'ReleaseNote')
    db_alias = schema_editor.connection.alias
    for note in release_notes:
        release_note_model.objects.using(db_alias).create(**note)


class Migration(migrations.Migration):

    dependencies = [
        ('admin_cohort', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReleaseNote',
            fields=[
                ('insert_datetime', models.DateTimeField(auto_now_add=True, null=True)),
                ('update_datetime', models.DateTimeField(auto_now=True, null=True)),
                ('delete_datetime', models.DateTimeField(blank=True, null=True)),
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('title', models.TextField()),
                ('message', django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), blank=True, size=None)),
                ('author', models.TextField(null=True)),
            ],
            options={
                'db_table': 'release_note',
            },
        ),
        migrations.RunPython(code=create_old_release_notes)
    ]
