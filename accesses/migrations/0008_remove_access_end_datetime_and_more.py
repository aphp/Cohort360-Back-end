# Generated by Django 4.1.7 on 2023-08-11 15:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accesses', '0007_unify_access_datetime_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='access',
            name='end_datetime',
        ),
        migrations.RemoveField(
            model_name='access',
            name='manual_end_datetime',
        ),
        migrations.RemoveField(
            model_name='access',
            name='manual_start_datetime',
        ),
        migrations.RemoveField(
            model_name='access',
            name='start_datetime',
        ),
        migrations.RenameField(
            model_name='access',
            old_name='end_datetime_new',
            new_name='end_datetime',
        ),
        migrations.RenameField(
            model_name='access',
            old_name='start_datetime_new',
            new_name='start_datetime',
        ),
    ]
