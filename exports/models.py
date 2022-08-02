from django.db import models
from django.db.models import CASCADE, SET_NULL

from admin_cohort.models import StrEnum, User, BaseModel, JobModelWithReview
from cohort.models import CohortResult
from workspaces.models import Account


class ExportType(StrEnum):
    CSV: str = "csv"
    HIVE: str = "hive"
    PSQL: str = "psql"


OUTPUT_FORMATS = [
    (ExportType.CSV.value, ExportType.CSV.value),
    (ExportType.HIVE.value, ExportType.HIVE.value),
    (ExportType.PSQL.value, ExportType.PSQL.value),
]

NEW_STATUS = "new"
VALIDATED_STATUS = "validated"
SUCCESS_STATUS = "done"
FAILED_STATUS = "failed"
DENIED_STATUS = "denied"

JOB_STATUTES = [
    (NEW_STATUS, NEW_STATUS),
    (VALIDATED_STATUS, VALIDATED_STATUS),
    (DENIED_STATUS, DENIED_STATUS),

    ("running", "running"),
    ("canceled", "canceled"),

    (SUCCESS_STATUS, SUCCESS_STATUS),
    (FAILED_STATUS, FAILED_STATUS),
    ("to delete", "to delete"),
    ("deleted", "deleted"),
]


class ExportRequest(JobModelWithReview, BaseModel, models.Model):
    id = models.BigAutoField(primary_key=True)
    motivation = models.TextField(null=True)
    output_format = models.CharField(
        choices=OUTPUT_FORMATS, default=ExportType.CSV.value, max_length=20)
    nominative = models.BooleanField(default=False)
    owner: User = models.ForeignKey(User, related_name='export_requests',
                                    on_delete=CASCADE, null=True)

    # OMOP
    cohort_fk: CohortResult = models.ForeignKey(
        CohortResult, related_name='export_requests', on_delete=SET_NULL,
        null=True)
    shift_dates = models.BooleanField(default=False)

    # USERS
    target_unix_account: Account = models.ForeignKey(
        Account, related_name='export_requests', on_delete=SET_NULL, null=True)
    creator_fk = models.ForeignKey(User, related_name='created_export_requests',
                                   on_delete=SET_NULL, null=True)
    is_user_notified = models.BooleanField(default=False)

    target_location = models.TextField(null=True)
    target_name = models.TextField(null=True)
    cleaned_at = models.DateTimeField(null=True)
    execution_request_datetime = models.DateTimeField(null=True)

    # to deprecated
    # to remove when infra is ready
    cohort_id = models.BigIntegerField(null=False)
    provider_id = models.BigIntegerField(null=True)
    status = models.CharField(choices=JOB_STATUTES, default=NEW_STATUS,
                              max_length=20)
    status_info = models.TextField(null=True)

    class Meta:
        managed = True
        db_table = 'export_request'

    def __str__(self):
        return f"{self.id}: cohort {self.cohort_fk.fhir_group_id} - " \
               f"{self.new_request_job_status}"

    @property
    def target_full_path(self) -> str:
        return f"{self.target_location}{self.target_name}" if (
                    self.target_location is not None
                    and self.target_name is not None
        ) else ""


class ExportRequestTable(models.Model):
    export_request_table_id = models.BigAutoField(primary_key=True)
    omop_table_name = models.TextField()
    source_table_name = models.TextField(null=True)
    export_request: ExportRequest = models.ForeignKey(
        ExportRequest, related_name="tables", on_delete=CASCADE)

    class Meta:
        managed = True
        db_table = 'export_request_table'
