# Generated by Django 4.1.7 on 2023-05-11 16:44

from django.conf import settings
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FactRelationShip',
            fields=[
                ('row_id', models.BigIntegerField(primary_key=True, serialize=False)),
                ('fact_id_1', models.BigIntegerField()),
                ('fact_id_2', models.BigIntegerField()),
            ],
            options={
                'db_table': 'fact_relationship',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Folder',
            fields=[
                ('uuid', models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('deleted', models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=50)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='folders', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Request',
            fields=[
                ('uuid', models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('deleted', models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('favorite', models.BooleanField(default=False)),
                ('data_type_of_query', models.CharField(choices=[('PATIENT', 'FHIR Patient'), ('ENCOUNTER', 'FHIR Encounter')], default='PATIENT', max_length=9)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_requests', to=settings.AUTH_USER_MODEL)),
                ('parent_folder', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='requests', to='cohort.folder')),
                ('shared_by', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='shared_requests', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='RequestQuerySnapshot',
            fields=[
                ('uuid', models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('deleted', models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('serialized_query', models.TextField(default='{}')),
                ('is_active_branch', models.BooleanField(default=True)),
                ('perimeters_ids', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=15), blank=True, null=True, size=None)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_request_query_snapshots', to=settings.AUTH_USER_MODEL)),
                ('previous_snapshot', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='next_snapshots', to='cohort.requestquerysnapshot')),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='query_snapshots', to='cohort.request')),
                ('shared_by', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='shared_query_snapshots', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='DatedMeasure',
            fields=[
                ('uuid', models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('deleted', models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('request_job_id', models.TextField(blank=True, null=True)),
                ('request_job_status', models.CharField(choices=[('new', 'new'), ('denied', 'denied'), ('validated', 'validated'), ('pending', 'pending'), ('long_pending', 'long_pending'), ('started', 'started'), ('failed', 'failed'), ('cancelled', 'cancelled'), ('finished', 'finished'), ('cleaned', 'cleaned'), ('unknown', 'unknown')], default='started', max_length=15, null=True)),
                ('request_job_fail_msg', models.TextField(blank=True, null=True)),
                ('request_job_duration', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('fhir_datetime', models.DateTimeField(null=True)),
                ('measure', models.BigIntegerField(null=True)),
                ('measure_min', models.BigIntegerField(null=True)),
                ('measure_max', models.BigIntegerField(null=True)),
                ('count_task_id', models.TextField(blank=True)),
                ('mode', models.CharField(choices=[('Snapshot', 'Snapshot'), ('Global', 'Global')], default='Snapshot', max_length=20, null=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_request_query_results', to=settings.AUTH_USER_MODEL)),
                ('request_query_snapshot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dated_measures', to='cohort.requestquerysnapshot')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='CohortResult',
            fields=[
                ('uuid', models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('deleted', models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('request_job_id', models.TextField(blank=True, null=True)),
                ('request_job_status', models.CharField(choices=[('new', 'new'), ('denied', 'denied'), ('validated', 'validated'), ('pending', 'pending'), ('long_pending', 'long_pending'), ('started', 'started'), ('failed', 'failed'), ('cancelled', 'cancelled'), ('finished', 'finished'), ('cleaned', 'cleaned'), ('unknown', 'unknown')], default='started', max_length=15, null=True)),
                ('request_job_fail_msg', models.TextField(blank=True, null=True)),
                ('request_job_duration', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(blank=True, max_length=255, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('favorite', models.BooleanField(default=False)),
                ('fhir_group_id', models.CharField(blank=True, max_length=64)),
                ('create_task_id', models.TextField(blank=True)),
                ('type', models.CharField(choices=[('IMPORT_I2B2', 'Previous cohorts imported from i2b2.'), ('MY_ORGANIZATIONS', 'Organizations in which I work (care sites with pseudo-anonymised reading rights).'), ('MY_PATIENTS', 'Patients that passed by all my organizations (care sites with nominative reading rights).'), ('MY_COHORTS', 'Cohorts I created in Cohort360')], default='MY_COHORTS', max_length=20)),
                ('dated_measure', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cohort', to='cohort.datedmeasure')),
                ('dated_measure_global', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='restricted_cohort', to='cohort.datedmeasure')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_cohorts', to=settings.AUTH_USER_MODEL)),
                ('request_query_snapshot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cohort_results', to='cohort.requestquerysnapshot')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
