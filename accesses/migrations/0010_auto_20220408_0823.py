# Generated by Django 2.2.16 on 2022-04-08 08:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accesses', '0009_auto_20220407_1708'),
        ('admin_cohort', '0006_manual_save_provider_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='access',
            name='source',
            field=models.TextField(blank=True, default='Manual', null=True),
        ),
        migrations.AlterField(
            model_name='profile',
            name='source',
            field=models.TextField(blank=True, default='Manual', null=True),
        ),
        migrations.RunSQL(
            "UPDATE access "
            "SET profile_id=provider_history_id"
        ),
        migrations.RunSQL(
            "UPDATE access "
            "SET role_fk_id=role_id"
        ),
        migrations.RunSQL(
            "UPDATE profile "
            "SET user_id=provider_source_value"
        ),
    ]
