# Generated by Django 4.1.7 on 2023-08-11 13:42

from django.db import migrations, models

unify_datetime_fields = """UPDATE accesses_access
                           SET start_datetime_new = COALESCE(manual_start_datetime, start_datetime),
                           end_datetime_new = COALESCE(manual_end_datetime, end_datetime)
                        """


class Migration(migrations.Migration):

    dependencies = [
        ('accesses', '0005_perimeter_level'),
    ]

    operations = [
        migrations.AddField(
            model_name='access',
            name='end_datetime_new',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='access',
            name='start_datetime_new',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunSQL(sql=unify_datetime_fields)
    ]
