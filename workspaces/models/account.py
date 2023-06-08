from django.db import models
from django.db.models import SET_NULL

from workspaces.models.jupyter_machine import JupyterMachine
from workspaces.models.kernel import Kernel
from workspaces.models.ldap_group import LdapGroup
from workspaces.models.project import Project
from workspaces.models.ranger_hive_policy import RangerHivePolicy


class Account(models.Model):
    uid = models.AutoField(primary_key=True)
    username = models.CharField(max_length=63, unique=True)
    name = models.CharField(max_length=63, null=True, blank=True)
    firstname = models.CharField(max_length=63, null=True, blank=True)
    lastname = models.CharField(max_length=63, null=True, blank=True)
    mail = models.CharField(max_length=63, null=True, blank=True)
    gid = models.BigIntegerField(null=True, blank=True)
    group = models.CharField(max_length=63, null=True, blank=True)
    home = models.TextField(null=False)
    project = models.ForeignKey(Project, on_delete=SET_NULL, null=True)
    conda_enable = models.BooleanField(default=False)
    conda_py_version = models.CharField(max_length=64, blank=True, null=False, default="3.7")
    conda_r = models.BooleanField(default=False)
    kernels = models.ManyToManyField(Kernel, related_name='users_uids')
    ssh = models.BooleanField(default=False)
    jupyter_machines = models.ManyToManyField(JupyterMachine, related_name='users_uids')
    ldap_groups = models.ManyToManyField(LdapGroup, related_name='users_uids', blank=True)
    brat_port = models.IntegerField(null=True)
    tensorboard_port = models.IntegerField(null=True)
    airflow_port = models.IntegerField(null=True)
    db_imagerie = models.BooleanField(default=False)
    ranger_hive_policy = models.ForeignKey(RangerHivePolicy, related_name='users_uids', on_delete=SET_NULL, null=True)
    aphp_ldap_group_dn = models.CharField(max_length=255)
    spark_port_start = models.IntegerField(null=False)
