# Generated by Django 2.2.16 on 2022-09-06 13:13

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cohort', '0012_auto_20220513_0854'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='folder',
            unique_together={('owner', 'name', 'parent_folder')},
        ),
    ]
