# Generated by Django 4.1.10 on 2023-08-17 12:52

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cohort', '0006_fhirfilter'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fhirfilter',
            name='owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fhir_filters', to=settings.AUTH_USER_MODEL),
        ),
    ]
