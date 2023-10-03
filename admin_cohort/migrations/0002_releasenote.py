# Generated by Django 4.1.7 on 2023-10-03 12:21

import django.contrib.postgres.fields
from django.db import migrations, models


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
                ('footer', models.TextField()),
            ],
            options={
                'db_table': 'release_note',
            },
        ),
    ]
