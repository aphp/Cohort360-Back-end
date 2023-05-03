from typing import Union

from django.db import models
from django.db.models import SET_NULL
from django.utils import timezone

from admin_cohort.models import User
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


class JobModelWithReview(JobModel):
    reviewer_fk = models.ForeignKey(User, related_name='reviewed_export_requests', on_delete=SET_NULL, null=True)
    review_request_datetime = models.DateTimeField(null=True)

    class Meta:
        abstract = True

    def validate(self, reviewer: Union[User, None] = None):
        self.reviewer_fk = reviewer
        self.review_request_datetime = timezone.now()
        return super(JobModelWithReview, self).validate()

    def deny(self, reviewer: Union[User, None] = None):
        self.reviewer_fk = reviewer
        self.review_request_datetime = timezone.now()
        return super(JobModelWithReview, self).deny()
