# Generated by Django 4.1.7 on 2023-03-29 13:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exports', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exportrequest',
            name='output_format',
            field=models.CharField(choices=[('csv', 'csv'), ('hive', 'hive')], default='csv', max_length=20),
        ),
    ]
