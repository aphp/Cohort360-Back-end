# Generated by Django 2.2.16 on 2022-04-28 13:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cohort', '0009_request_shared_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='cohortresult',
            name='new_request_job_status',
            field=models.CharField(choices=[
                ('new', 'new'), ('denied', 'denied'),
                ('validated', 'validated'), ('pending', 'pending'),
                ('started', 'started'), ('failed', 'failed'),
                ('cancelled', 'cancelled'), ('finished', 'finished'),
                ('cleaned', 'cleaned'), ('unknown', 'unknown')],
                default='pending', max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='datedmeasure',
            name='new_request_job_status',
            field=models.CharField(choices=[
                ('new', 'new'), ('denied', 'denied'),
                ('validated', 'validated'), ('pending', 'pending'),
                ('started', 'started'), ('failed', 'failed'),
                ('cancelled', 'cancelled'), ('finished', 'finished'),
                ('cleaned', 'cleaned'), ('unknown', 'unknown')],
                default='pending', max_length=10, null=True),
        ),
    ]
