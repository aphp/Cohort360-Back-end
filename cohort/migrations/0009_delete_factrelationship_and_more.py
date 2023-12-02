# Generated by Django 4.1.11 on 2023-11-24 08:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cohort', '0008_alter_DM_related_names'),
    ]

    operations = [
        migrations.DeleteModel(
            name='FactRelationShip',
        ),
        migrations.AlterUniqueTogether(
            name='fhirfilter',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='fhirfilter',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted__isnull', True)), fields=('name', 'fhir_resource', 'owner'),
                                               name='unique_name_fhir_resource_owner'),
        ),
    ]