from django.db import models

RHP_TYPE_DEFAULT_USER = 'default_user'
RHP_TYPE_DEFAULT_CSE = 'default_cse'
RHP_TYPE_DEFAULT_DSIP = 'default_dsip'
RHP_TYPE_DEFAULT_BDR = 'default_bdr'

PROJECT_STATUS_NEW = "new"
PROJECT_STATUS_VALIDATED = "validated"
PROJECT_STATUS_NOT_VALIDATED = "not_validated"
PROJECT_STATUS_ABORTED = "aborted"
PROJECT_STATUS_IN_PROGRESS = "in progress"
PROJECT_STATUS_CLOSED = "closed"

PROJECT_STATUS_TRANSITIONS = {PROJECT_STATUS_NEW: [PROJECT_STATUS_VALIDATED, PROJECT_STATUS_ABORTED],
                              PROJECT_STATUS_VALIDATED: [PROJECT_STATUS_IN_PROGRESS],
                              PROJECT_STATUS_NOT_VALIDATED: [PROJECT_STATUS_NEW],
                              PROJECT_STATUS_ABORTED: [PROJECT_STATUS_CLOSED],
                              PROJECT_STATUS_IN_PROGRESS: [PROJECT_STATUS_CLOSED],
                              PROJECT_STATUS_CLOSED: [PROJECT_STATUS_IN_PROGRESS]}

RHP_TYPE_CHOICES = ((RHP_TYPE_DEFAULT_USER, RHP_TYPE_DEFAULT_USER),
                    (RHP_TYPE_DEFAULT_CSE, RHP_TYPE_DEFAULT_CSE),
                    (RHP_TYPE_DEFAULT_DSIP, RHP_TYPE_DEFAULT_DSIP),
                    (RHP_TYPE_DEFAULT_BDR, RHP_TYPE_DEFAULT_BDR))

PROJECT_STATUS_CHOICE = ((PROJECT_STATUS_NEW, PROJECT_STATUS_NEW),
                         (PROJECT_STATUS_VALIDATED, PROJECT_STATUS_VALIDATED),
                         (PROJECT_STATUS_NOT_VALIDATED, PROJECT_STATUS_NOT_VALIDATED),
                         (PROJECT_STATUS_ABORTED, PROJECT_STATUS_ABORTED),
                         (PROJECT_STATUS_IN_PROGRESS, PROJECT_STATUS_IN_PROGRESS),
                         (PROJECT_STATUS_CLOSED, PROJECT_STATUS_CLOSED))


class Project(models.Model):
    uid = models.AutoField(primary_key=True)
    type = models.CharField(max_length=63, choices=RHP_TYPE_CHOICES)
    identifier = models.CharField(max_length=63, unique=True)
    acronym = models.CharField(max_length=63, blank=True)
    title = models.TextField(blank=True)
    thematic = models.CharField(max_length=63, blank=True)
    description = models.TextField(blank=True)
    # instigator_id = models.BigIntegerField()  # A provider_id
    status = models.CharField(choices=PROJECT_STATUS_CHOICE, default=PROJECT_STATUS_NEW, max_length=20)
    operation_actors = models.TextField(blank=True)
    partners = models.TextField(blank=True)
    lawfulness_of_processing = models.TextField(blank=True)
    data_recipients = models.TextField(blank=True)
    data_conservation_duration = models.DurationField(null=True)
    insert_datetime = models.DateTimeField(auto_now_add=True)
    validation_date = models.DateTimeField(null=True)
