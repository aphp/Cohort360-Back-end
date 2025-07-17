from django.db import models
from admin_cohort.types import JobStatus

JOB_STATUSES = [(e.value, e.value) for e in JobStatus]


class JobModel(models.Model):
    request_job_id = models.TextField(blank=True)
    request_job_status = models.CharField(max_length=15, choices=JOB_STATUSES, default=JobStatus.new)
    request_job_fail_msg = models.TextField(blank=True)
    request_job_duration = models.TextField(blank=True)

    class Meta:
        abstract = True
