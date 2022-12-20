from django.db import models


POLICY_TYPES = (('default_user', 'default_user'),
                ('default_cse', 'default_cse'),
                ('default_dsip', 'default_dsip'),
                ('default_bdr', 'default_bdr'))


class RangerHivePolicy(models.Model):
    policy_type = models.CharField(max_length=63, choices=POLICY_TYPES)
    db = models.CharField(max_length=63, null=True)
    db_tables = models.CharField(max_length=63, null=True)
    db_imagerie = models.CharField(max_length=63, null=True)
    db_work = models.CharField(max_length=63, null=True)
