# Generated by Django 5.0.4 on 2024-07-12 13:48

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CareSite',
            fields=[
                ('care_site_id', models.BigIntegerField(primary_key=True, serialize=False)),
                ('care_site_source_value', models.TextField(blank=True, null=True)),
                ('care_site_name', models.TextField(blank=True, null=True)),
                ('care_site_short_name', models.TextField(blank=True, null=True)),
                ('care_site_type_source_value', models.TextField(blank=True, null=True)),
                ('care_site_parent_id', models.BigIntegerField(null=True)),
                ('cohort_id', models.BigIntegerField(null=True)),
                ('cohort_size', models.BigIntegerField(null=True)),
                ('delete_datetime', models.DateTimeField(null=True)),
            ],
            options={
                'db_table': 'care_site',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Concept',
            fields=[
                ('concept_id', models.IntegerField(primary_key=True, serialize=False)),
                ('concept_name', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'concept',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='FactRelationship',
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
    ]
