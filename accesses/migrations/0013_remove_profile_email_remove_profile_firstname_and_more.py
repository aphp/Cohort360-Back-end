# Generated by Django 4.2.11 on 2024-04-17 08:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accesses', '0012_remove_old_rights_add_unique_constraint'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='email',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='firstname',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='lastname',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='provider_id',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='provider_name',
        ),
    ]
