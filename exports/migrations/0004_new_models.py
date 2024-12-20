# Generated by Django 4.1.7 on 2023-08-30 14:53

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('cohort', '0006_fhirfilter'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('exports', '0003_set_request_job_status_to_new'),
    ]

    operations = [
        migrations.CreateModel(
            name='InfrastructureProvider',
            fields=[
                ('uuid', models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('deleted', models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
            ],
            options={
                'db_table': 'infrastructure_provider',
            },
        ),
        migrations.CreateModel(
            name='Datalab',
            fields=[
                ('uuid', models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('deleted', models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('infrastructure_provider', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='datalabs',
                                                              to='exports.infrastructureprovider'))
            ],
            options={
                'db_table': 'datalab',
            },
        ),
        migrations.CreateModel(
            name='Export',
            fields=[
                ('uuid', models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('deleted', models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('motivation', models.TextField(null=True)),
                ('clean_datetime', models.DateTimeField(null=True)),
                ('status', models.CharField(choices=[('PENDING', 'En attente'), ('SENT_TO_DE', 'Envoyé au DataExporter'), ('DELIVERED', 'Livré')], max_length=55)),
                ('output_format', models.CharField(choices=[('csv', 'csv'), ('hive', 'hive')], max_length=20)),
                ('target_name', models.CharField(max_length=255, null=True)),
                ('target_location', models.TextField(null=True)),
                ('data_exporter_version', models.CharField(max_length=20, null=True)),
                ('data_version', models.CharField(max_length=20, null=True)),
                ('nominative', models.BooleanField(default=False)),
                ('shift_dates', models.BooleanField(default=False)),
                ('is_user_notified', models.BooleanField(default=False)),
                ('datalab', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='exports', to='exports.datalab')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exports', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'export',
            },
        ),
        migrations.CreateModel(
            name='ExportTable',
            fields=[
                ('uuid', models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('deleted', models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=55)),
                ('respect_table_relationships', models.BooleanField(default=True)),
                ('cohort_result_subset', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='export_tables', to='cohort.cohortresult')),
                ('export', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='export_tables', to='exports.export')),
                ('fhir_filter', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='export_tables', to='cohort.fhirfilter')),
            ],
            options={
                'db_table': 'export_table',
            },
        ),
        migrations.CreateModel(
            name='ExportResultStat',
            fields=[
                ('uuid', models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('deleted', models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=55)),
                ('type', models.CharField(choices=[('Integer', 'Integer'), ('Text', 'Text'), ('SizeBytes', 'SizeBytes')], max_length=20)),
                ('value', models.CharField(max_length=55)),
                ('export', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stats', to='exports.export')),
            ],
            options={
                'db_table': 'export_result_stat',
            },
        ),
    ]
