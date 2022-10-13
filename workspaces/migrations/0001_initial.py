# Generated by Django 2.2.28 on 2022-10-13 11:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='JupyterMachine',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=60)),
            ],
        ),
        migrations.CreateModel(
            name='Kernel',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='LdapGroup',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('uid', models.AutoField(primary_key=True, serialize=False)),
                ('type', models.CharField(choices=[('default_user', 'default_user'), ('default_cse', 'default_cse'),
                                                   ('default_dsip', 'default_dsip'), ('default_bdr', 'default_bdr')],
                                          max_length=63)),
                ('identifier', models.CharField(max_length=63, unique=True)),
                ('acronym', models.CharField(blank=True, max_length=63)),
                ('title', models.TextField(blank=True)),
                ('thematic', models.CharField(blank=True, max_length=63)),
                ('description', models.TextField(blank=True)),
                ('status', models.CharField(
                    choices=[('new', 'new'), ('validated', 'validated'), ('not_validated', 'not_validated'),
                             ('aborted', 'aborted'), ('in progress', 'in progress'), ('closed', 'closed')],
                    default='new', max_length=20)),
                ('operation_actors', models.TextField(blank=True)),
                ('partners', models.TextField(blank=True)),
                ('lawfulness_of_processing', models.TextField(blank=True)),
                ('data_recipients', models.TextField(blank=True)),
                ('data_conservation_duration', models.DurationField(null=True)),
                ('insert_datetime', models.DateTimeField(auto_now_add=True)),
                ('validation_date', models.DateTimeField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='RangerHivePolicy',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('policy_type', models.CharField(
                    choices=[('default_user', 'default_user'), ('default_cse', 'default_cse'),
                             ('default_dsip', 'default_dsip'), ('default_bdr', 'default_bdr')], max_length=63)),
                ('db', models.CharField(max_length=63, null=True)),
                ('db_tables', models.CharField(max_length=63, null=True)),
                ('db_imagerie', models.CharField(max_length=63, null=True)),
                ('db_work', models.CharField(max_length=63, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Account',
            fields=[
                ('uid', models.AutoField(primary_key=True, serialize=False)),
                ('username', models.CharField(max_length=63, unique=True)),
                ('name', models.CharField(blank=True, max_length=63, null=True)),
                ('firstname', models.CharField(blank=True, max_length=63, null=True)),
                ('lastname', models.CharField(blank=True, max_length=63, null=True)),
                ('mail', models.CharField(blank=True, max_length=63, null=True)),
                ('gid', models.BigIntegerField(blank=True, null=True)),
                ('group', models.CharField(blank=True, max_length=63, null=True)),
                ('home', models.TextField()),
                ('conda_enable', models.BooleanField(default=False)),
                ('conda_py_version', models.CharField(blank=True, default='3.7', max_length=64)),
                ('conda_r', models.BooleanField(default=False)),
                ('ssh', models.BooleanField(default=False)),
                ('brat_port', models.IntegerField(null=True)),
                ('tensorboard_port', models.IntegerField(null=True)),
                ('airflow_port', models.IntegerField(null=True)),
                ('db_imagerie', models.BooleanField(default=False)),
                ('aphp_ldap_group_dn', models.CharField(max_length=255)),
                ('spark_port_start', models.IntegerField()),
                ('jupyter_machines', models.ManyToManyField(related_name='users_uids', to='workspaces.JupyterMachine')),
                ('kernels', models.ManyToManyField(related_name='users_uids', to='workspaces.Kernel')),
                ('ldap_groups',
                 models.ManyToManyField(blank=True, related_name='users_uids', to='workspaces.LdapGroup')),
                ('project',
                 models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='workspaces.Project')),
                ('ranger_hive_policy',
                 models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='users_uids',
                                   to='workspaces.RangerHivePolicy')),
            ],
        ),
    ]
