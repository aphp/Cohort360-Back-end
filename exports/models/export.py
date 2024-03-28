from datetime import timedelta

from django.db import models
from django.db.models import CASCADE
from django.utils import timezone

from admin_cohort.models import User, JobModel
from admin_cohort.settings import DAYS_TO_KEEP_EXPORTED_FILES
from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from exports.models import ExportsBaseModel, Datalab
from exports.types import ExportStatus, ExportType

STATUSES = [(status.name, status.value) for status in ExportStatus]
OUTPUT_FORMATS = [(out_format.value, out_format.value) for out_format in ExportType]


class Export(ExportsBaseModel, JobModel):
    owner = models.ForeignKey(to=User, related_name="exports", on_delete=CASCADE)
    output_format = models.CharField(null=False, choices=OUTPUT_FORMATS, max_length=20)
    status = models.CharField(choices=STATUSES, default=ExportStatus.PENDING, max_length=55, null=True)
    target_name = models.CharField(null=True, max_length=255)
    target_location = models.TextField(null=True)
    data_exporter_version = models.CharField(null=True, max_length=20)
    data_version = models.CharField(null=True, max_length=20)
    nominative = models.BooleanField(null=False, default=False)
    is_user_notified = models.BooleanField(null=False, default=False)

    # Jupyter
    datalab = models.ForeignKey(to=Datalab, related_name="exports", on_delete=CASCADE, null=True)
    shift_dates = models.BooleanField(null=False, default=False)

    # CSV
    motivation = models.TextField(null=True, blank=True)
    clean_datetime = models.DateTimeField(null=True)

    class Meta:
        db_table = 'export'

    @property
    def target_full_path(self) -> str:
        if self.target_location and self.target_name:
            extensions = {ExportType.CSV.value: ".zip",
                          ExportType.HIVE.value: ".db"
                          }
            return f"{self.target_location}/{self.target_name}{extensions.get(self.output_format)}"
        return ""

    @property
    def target_datalab(self) -> str:
        return self.datalab and self.datalab.name or ""

    @property
    def cohort_name(self) -> str:
        cohort = CohortResult.objects.filter(fhir_group_id=self.cohort_id).first()
        return cohort and cohort.name or ""

    def downloadable(self) -> bool:
        return self.request_job_status == JobStatus.finished \
               and self.output_format == ExportType.CSV

    def available_for_download(self) -> bool:
        return self.created_at + timedelta(days=DAYS_TO_KEEP_EXPORTED_FILES) > timezone.now()
