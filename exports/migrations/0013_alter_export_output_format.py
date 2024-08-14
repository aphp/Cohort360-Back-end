# Generated by Django 5.0.8 on 2024-08-13 14:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exports', '0012_remove_exportrequesttable_export_request_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='export',
            name='output_format',
            field=models.CharField(choices=[('csv', 'csv'), ('xlsx', 'xlsx'), ('hive', 'hive')], max_length=20),
        ),
    ]