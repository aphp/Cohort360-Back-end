# Generated by Django 2.2.16 on 2022-09-16 18:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cohort', '0015_auto_20220916_1758'),
    ]

    operations = [
        migrations.RenameField(
            model_name='cohortresult',
            old_name='new_request_job_status',
            new_name='request_job_status',
        ),
        migrations.RenameField(
            model_name='datedmeasure',
            old_name='new_request_job_status',
            new_name='request_job_status',
        ),
    ]
