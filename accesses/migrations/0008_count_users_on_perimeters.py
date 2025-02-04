# Generated by Django 4.1.7 on 2023-08-22 13:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accesses', '0007_remove_access_end_datetime_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='perimeter',
            name='count_allowed_users',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
        migrations.AddField(
            model_name='perimeter',
            name='count_allowed_users_above_levels',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
        migrations.AddField(
            model_name='perimeter',
            name='count_allowed_users_inferior_levels',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
    ]
