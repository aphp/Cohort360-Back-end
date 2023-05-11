# Generated by Django 4.1.7 on 2023-05-11 15:03

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('cohort', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('workspaces', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExportRequest',
            fields=[
                ('insert_datetime', models.DateTimeField(auto_now_add=True, null=True)),
                ('update_datetime', models.DateTimeField(auto_now=True, null=True)),
                ('delete_datetime', models.DateTimeField(blank=True, null=True)),
                ('request_job_id', models.TextField(blank=True, null=True)),
                ('request_job_status', models.CharField(choices=[('new', 'new'), ('denied', 'denied'), ('validated', 'validated'),
                                                                 ('pending', 'pending'), ('long_pending', 'long_pending'), ('started', 'started'),
                                                                 ('failed', 'failed'), ('cancelled', 'cancelled'), ('finished', 'finished'),
                                                                 ('cleaned', 'cleaned'), ('unknown', 'unknown')], default='new', max_length=15,
                                                        null=True)),
                ('request_job_fail_msg', models.TextField(blank=True, null=True)),
                ('request_job_duration', models.TextField(blank=True, null=True)),
                ('review_request_datetime', models.DateTimeField(null=True)),
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('motivation', models.TextField(null=True)),
                ('output_format', models.CharField(choices=[('csv', 'csv'), ('hive', 'hive')], default='csv', max_length=20)),
                ('nominative', models.BooleanField(default=False)),
                ('shift_dates', models.BooleanField(default=False)),
                ('is_user_notified', models.BooleanField(default=False)),
                ('target_location', models.TextField(null=True)),
                ('target_name', models.TextField(null=True)),
                ('cleaned_at', models.DateTimeField(null=True)),
                ('execution_request_datetime', models.DateTimeField(null=True)),
                ('cohort_id', models.BigIntegerField()),
                ('provider_id', models.CharField(blank=True, max_length=25, null=True)),
                ('cohort_fk', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='export_requests',
                                                to='cohort.cohortresult')),
                ('creator_fk', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_export_requests',
                                                 to=settings.AUTH_USER_MODEL)),
                ('owner', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='export_requests',
                                            to=settings.AUTH_USER_MODEL)),
                ('reviewer_fk', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_export_requests',
                                                  to=settings.AUTH_USER_MODEL)),
                ('target_unix_account', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='export_requests',
                                                          to='workspaces.account')),
            ],
            options={
                'db_table': 'export_request',
            },
        ),
        migrations.CreateModel(
            name='ExportRequestTable',
            fields=[
                ('export_request_table_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('omop_table_name', models.TextField()),
                ('source_table_name', models.TextField(null=True)),
                ('export_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tables', to='exports.exportrequest')),
            ],
            options={
                'db_table': 'export_request_table',
            },
        ),
    ]
