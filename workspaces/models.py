from django.db import models
from django.db.models import SET_NULL

RHP_TYPE_DEFAULT_USER = 'default_user'
RHP_TYPE_DEFAULT_CSE = 'default_cse'
RHP_TYPE_DEFAULT_DSIP = 'default_dsip'
RHP_TYPE_DEFAULT_BDR = 'default_bdr'
RHP_TYPE_CHOICES = (
    (RHP_TYPE_DEFAULT_USER, RHP_TYPE_DEFAULT_USER),
    (RHP_TYPE_DEFAULT_CSE, RHP_TYPE_DEFAULT_CSE),
    (RHP_TYPE_DEFAULT_DSIP, RHP_TYPE_DEFAULT_DSIP),
    (RHP_TYPE_DEFAULT_BDR, RHP_TYPE_DEFAULT_BDR),
)

PROJECT_STATUS_NEW = "new"
PROJECT_STATUS_VALIDATED = "validated"
PROJECT_STATUS_NOT_VALIDATED = "not_validated"
PROJECT_STATUS_ABORTED = "aborted"
PROJECT_STATUS_IN_PROGRESS = "in progress"
PROJECT_STATUS_CLOSED = "closed"

PROJECT_STATUS_TRANSITIONS = {
    PROJECT_STATUS_NEW: [PROJECT_STATUS_VALIDATED, PROJECT_STATUS_ABORTED],
    PROJECT_STATUS_VALIDATED: [PROJECT_STATUS_IN_PROGRESS],
    PROJECT_STATUS_NOT_VALIDATED: [PROJECT_STATUS_NEW],
    PROJECT_STATUS_ABORTED: [PROJECT_STATUS_CLOSED],
    PROJECT_STATUS_IN_PROGRESS: [PROJECT_STATUS_CLOSED],
    PROJECT_STATUS_CLOSED: [PROJECT_STATUS_IN_PROGRESS],
}

PROJECT_STATUS_CHOICE = [
    (PROJECT_STATUS_NEW, PROJECT_STATUS_NEW),
    (PROJECT_STATUS_VALIDATED, PROJECT_STATUS_VALIDATED),
    (PROJECT_STATUS_NOT_VALIDATED, PROJECT_STATUS_NOT_VALIDATED),
    (PROJECT_STATUS_ABORTED, PROJECT_STATUS_ABORTED),
    (PROJECT_STATUS_IN_PROGRESS, PROJECT_STATUS_IN_PROGRESS),
    (PROJECT_STATUS_CLOSED, PROJECT_STATUS_CLOSED),
]


class Project(models.Model):
    uid = models.AutoField(primary_key=True)
    # Same choices with RangerHivePolicy
    type = models.CharField(max_length=63, choices=RHP_TYPE_CHOICES)
    # For example: "cse180001"
    identifier = models.CharField(max_length=63, unique=True)
    # For example "covisan"
    acronym = models.CharField(max_length=63, blank=True)
    # For example "Predict mortality of covid"
    title = models.TextField(blank=True)
    # For example "internship" or "cancer" or "radiology" ...
    thematic = models.CharField(max_length=63, blank=True)
    description = models.TextField(blank=True)
    # FIXME: link to a user or provider?
    # instigator_id = models.BigIntegerField()  # A provider_id

    status = models.CharField(choices=PROJECT_STATUS_CHOICE,
                              default=PROJECT_STATUS_NEW, max_length=20)

    # Optional supplementary attributes of a project
    operation_actors = models.TextField(blank=True)
    partners = models.TextField(blank=True)
    lawfulness_of_processing = models.TextField(blank=True)
    data_recipients = models.TextField(blank=True)
    data_conservation_duration = models.DurationField(null=True)

    insert_datetime = models.DateTimeField(auto_now_add=True)
    validation_date = models.DateTimeField(null=True)


class JupyterMachine(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=60, null=False)


class RangerHivePolicy(models.Model):
    policy_type = models.CharField(max_length=63, choices=(
        ('default_user', 'default_user'),
        ('default_cse', 'default_cse'),
        ('default_dsip', 'default_dsip'),
        ('default_bdr', 'default_bdr'),
    ))
    db = models.CharField(max_length=63, null=True)
    db_tables = models.CharField(max_length=63, null=True)
    db_imagerie = models.CharField(max_length=63, null=True)
    db_work = models.CharField(max_length=63, null=True)


class LdapGroup(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)


class Kernel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)


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
    conda_py_version = models.CharField(
        max_length=64, blank=True, null=False, default="3.7"
    )
    conda_r = models.BooleanField(default=False)

    kernels = models.ManyToManyField(Kernel, related_name='users_uids')

    ssh = models.BooleanField(default=False)
    jupyter_machines = models.ManyToManyField(
        JupyterMachine, related_name='users_uids'
    )
    ldap_groups = models.ManyToManyField(
        LdapGroup, related_name='users_uids', blank=True
    )
    brat_port = models.IntegerField(null=True)
    tensorboard_port = models.IntegerField(null=True)
    airflow_port = models.IntegerField(null=True)
    db_imagerie = models.BooleanField(default=False)
    ranger_hive_policy = models.ForeignKey(
        RangerHivePolicy, related_name='users_uids', on_delete=SET_NULL,
        null=True
    )

    aphp_ldap_group_dn = models.CharField(max_length=255)
    spark_port_start = models.IntegerField(null=False)
