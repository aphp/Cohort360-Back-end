# Generated by Django 2.2.16 on 2022-04-08 11:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accesses', '0010_auto_20220408_0823'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='access',
            name='provider_history_id',
        ),
        migrations.RemoveField(
            model_name='access',
            name='role_id',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='provider_source_value',
        ),
    ]
