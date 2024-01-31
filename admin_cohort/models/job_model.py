from django.db import models
from admin_cohort.types import JobStatus, WorkflowError

JOB_STATUSES = [(e.value, e.value) for e in JobStatus]


class JobModel(models.Model):
    request_job_id = models.TextField(blank=True, null=True)
    request_job_status = models.CharField(max_length=15, choices=JOB_STATUSES, default=JobStatus.new.value, null=True)
    request_job_fail_msg = models.TextField(blank=True, null=True)
    request_job_duration = models.TextField(blank=True, null=True)

    class Meta:
        abstract = True

    def validate(self):
        if self.request_job_status != JobStatus.new:
            raise WorkflowError(f"Job can be validated only if current status is '{JobStatus.new}'."
                                f"Current status is '{self.request_job_status}'")
        self.request_job_status = JobStatus.validated
        self.save()

    def deny(self):
        if self.request_job_status != JobStatus.new:
            raise WorkflowError(f"Job can be denied only if current status is {JobStatus.new}'."
                                f"Current status is '{self.request_job_status}'")
        self.request_job_status = JobStatus.denied
        self.save()
