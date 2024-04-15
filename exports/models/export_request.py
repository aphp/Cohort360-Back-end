from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import CASCADE, SET_NULL
from django.utils import timezone

from admin_cohort.models import JobModel, BaseModel, User
from cohort.models import CohortResult
from workspaces.models import Account
from exports import ExportTypes

OUTPUT_FORMATS = [(t.value, t.value) for t in ExportTypes]


class ExportRequest(JobModel, BaseModel, models.Model):
    id = models.BigAutoField(primary_key=True)
    motivation = models.TextField(null=True)
    output_format = models.CharField(choices=OUTPUT_FORMATS, max_length=20)
    nominative = models.BooleanField(default=False)
    owner = models.ForeignKey(User, related_name='export_requests', on_delete=CASCADE, null=True)
    cohort_fk = models.ForeignKey(CohortResult, related_name='export_requests', on_delete=SET_NULL, null=True)
    shift_dates = models.BooleanField(default=False)
    target_unix_account = models.ForeignKey(Account, related_name='export_requests', on_delete=SET_NULL, null=True)
    creator_fk = models.ForeignKey(User, related_name='created_export_requests', on_delete=SET_NULL, null=True)
    is_user_notified = models.BooleanField(default=False)
    target_location = models.TextField(null=True)
    target_name = models.TextField(null=True)
    cleaned_at = models.DateTimeField(null=True)
    execution_request_datetime = models.DateTimeField(null=True)
    cohort_id = models.BigIntegerField(null=False)
    provider_id = models.CharField(max_length=25, blank=True, null=True)
    reviewer_fk = models.ForeignKey(User, related_name='reviewed_export_requests', on_delete=SET_NULL, null=True)
    review_request_datetime = models.DateTimeField(null=True)

    class Meta:
        db_table = 'export_request'

    def __str__(self):
        return f"{self.id}: cohort {self.cohort_fk.fhir_group_id} - {self.request_job_status}"

    @property
    def target_full_path(self) -> str:
        if self.target_location and self.target_name:
            return f"{self.target_location}/{self.target_name}"
        return ""

    @property
    def cohort_name(self) -> str:
        cohort = CohortResult.objects.filter(fhir_group_id=self.cohort_id).first()
        return cohort and cohort.name or ""

    @property
    def patients_count(self) -> int:
        cohort = CohortResult.objects.filter(fhir_group_id=self.cohort_id).first()
        return cohort and cohort.dated_measure.measure or -1

    @property
    def target_env(self) -> str:
        return self.target_unix_account and self.target_unix_account.name or ""

    def available_for_download(self) -> bool:
        return self.insert_datetime + timedelta(days=settings.DAYS_TO_KEEP_EXPORTED_FILES) > timezone.now()
