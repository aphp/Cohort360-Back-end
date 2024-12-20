# Generated by Django 4.1.11 on 2023-11-03 11:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accesses', '0011_add_new_rights_and_rename_others'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='role',
            name='right_edit_roles',
        ),
        migrations.RemoveField(
            model_name='role',
            name='right_edit_users',
        ),
        migrations.RemoveField(
            model_name='role',
            name='right_manage_env_user_links',
        ),
        migrations.RemoveField(
            model_name='role',
            name='right_manage_review_export_csv',
        ),
        migrations.RemoveField(
            model_name='role',
            name='right_manage_review_transfer_jupyter',
        ),
        migrations.RemoveField(
            model_name='role',
            name='right_review_export_csv',
        ),
        migrations.RemoveField(
            model_name='role',
            name='right_review_transfer_jupyter',
        ),
        migrations.RemoveField(
            model_name='role',
            name='invalid_reason',
        ),
        migrations.AddConstraint(
            model_name='role',
            constraint=models.UniqueConstraint(condition=models.Q(('delete_datetime__isnull', True)), fields=('name',), name='unique_name'),
        ),
    ]
