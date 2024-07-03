# Generated by Django 4.2.11 on 2024-04-25 09:39

from django.db import migrations, models


mark_old_cohorts_as_non_subsets = "UPDATE cohort_cohortresult SET is_subset=False;"


class Migration(migrations.Migration):

    dependencies = [
        ('cohort', '0011_feasibility_study'),
    ]

    operations = [
        migrations.AddField(
            model_name='cohortresult',
            name='is_subset',
            field=models.BooleanField(default=False),
        ),
        migrations.RunSQL(sql=mark_old_cohorts_as_non_subsets)
    ]