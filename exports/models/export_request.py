from django.db import models
from django.db.models import CASCADE, SET_NULL

from admin_cohort.models import JobModelWithReview, BaseModel, User
from cohort.models import CohortResult
from exports.types import ExportType
from workspaces.models import Account

OUTPUT_FORMATS = [(ExportType.CSV.value, ExportType.CSV.value),
                  (ExportType.HIVE.value, ExportType.HIVE.value),
                  (ExportType.PSQL.value, ExportType.PSQL.value)]


class ExportRequest(JobModelWithReview, BaseModel, models.Model):
    id = models.BigAutoField(primary_key=True)
    motivation = models.TextField(null=True)
    output_format = models.CharField(choices=OUTPUT_FORMATS, default=ExportType.CSV.value, max_length=20)
    nominative = models.BooleanField(default=False)
    owner = models.ForeignKey(User, related_name='export_requests', on_delete=CASCADE, null=True)
    # OMOP
    cohort_fk = models.ForeignKey(CohortResult, related_name='export_requests', on_delete=SET_NULL, null=True)
    shift_dates = models.BooleanField(default=False)
    # USERS
    target_unix_account = models.ForeignKey(Account, related_name='export_requests', on_delete=SET_NULL, null=True)
    creator_fk = models.ForeignKey(User, related_name='created_export_requests', on_delete=SET_NULL, null=True)
    is_user_notified = models.BooleanField(default=False)
    target_location = models.TextField(null=True)
    target_name = models.TextField(null=True)
    cleaned_at = models.DateTimeField(null=True)
    execution_request_datetime = models.DateTimeField(null=True)
    # to deprecated
    # to remove when infra is ready
    cohort_id = models.BigIntegerField(null=False)
    provider_id = models.BigIntegerField(null=True)

    class Meta:
        db_table = 'export_request'

    def __str__(self):
        return f"{self.id}: cohort {self.cohort_fk.fhir_group_id} - {self.request_job_status}"

    @property
    def target_full_path(self) -> str:
        if self.target_location and self.target_name:
            return f"{self.target_location}/{self.target_name}.zip"
        return ""