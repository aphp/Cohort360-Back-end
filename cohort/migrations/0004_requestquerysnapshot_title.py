# Generated by Django 4.1.7 on 2023-06-22 12:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cohort', '0003_set_default_request_job_status_to_new'),
    ]

    operations = [
        migrations.AddField(
            model_name='requestquerysnapshot',
            name='title',
            field=models.CharField(default='', max_length=50),
        ),
    ]