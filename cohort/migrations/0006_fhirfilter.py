# Generated by Django 4.1.10 on 2023-08-10 09:32

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cohort', '0005_requestquerysnapshot_version'),
    ]

    operations = [
        migrations.CreateModel(
            name='FhirFilter',
            fields=[
                ('uuid', models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('deleted', models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('fhir_resource', models.CharField(max_length=255)),
                ('fhir_version', models.CharField(max_length=50)),
                ('name', models.CharField(max_length=50, validators=[django.core.validators.MinLengthValidator(2)])),
                ('filter', models.TextField()),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fhir_filters', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('fhir_resource', 'name', 'owner_id')},
            },
        ),
    ]
