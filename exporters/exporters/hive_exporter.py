import logging
from typing import List

from requests import RequestException

from admin_cohort.models import User
from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from exporters.exceptions import InvalidJobId, CreateHiveDBException, HiveDBOwnershipException
from exports.models import Export, Datalab
from exporters.exporters.base_exporter import BaseExporter
from exporters.enums import ExportTypes, APIJobType

_logger = logging.getLogger('django.request')


class HiveExporter(BaseExporter):

    def __init__(self):
        super().__init__()
        self.type = ExportTypes.HIVE
        self.target_location = self.hadoop_api.hive_db_path
        self.user = self.hadoop_api.hive_user

    def validate(self, export_data: dict, **kwargs) -> None:
        self.validate_tables_data(tables_data=export_data.get("export_tables", []))
        kwargs["source_cohorts_ids"] = [t.get("cohort_result_source")
                                        for t in export_data.get("export_tables", [])
                                        if t.get("cohort_result_source")]
        super().validate(export_data=export_data, **kwargs)

    def validate_tables_data(self, tables_data: List[dict]) -> bool:
        required_table = self.export_api.required_table
        base_cohort_provided = False
        required_table_provided = False
        for td in tables_data:
            source_cohort_id = td.get('cohort_result_source')

            if td.get("table_name", "") == required_table:
                required_table_provided = True
                if not source_cohort_id:
                    raise ValueError(f"The `{required_table}` table can not be exported without a source cohort")

            if source_cohort_id:
                if CohortResult.objects.filter(pk=source_cohort_id, request_job_status=JobStatus.finished).exists():
                    base_cohort_provided = True
                else:
                    raise ValueError(f"Cohort `{source_cohort_id}` not found or did not finish successfully")

        if not required_table_provided and not base_cohort_provided:
            raise ValueError(f"`{required_table}` table was not specified; must then provide source cohort for all tables")
        return True

    def complete_data(self, export_data: dict, owner: User, **kwargs) -> None:
        kwargs["target_name"] = Datalab.objects.get(pk=export_data["datalab"]).name
        super().complete_data(export_data=export_data, owner=owner, **kwargs)

    @staticmethod
    def get_db_location(export: Export) -> str:
        return f"{export.target_full_path}.db"

    def create_db(self, export: Export) -> None:
        db_location = self.get_db_location(export=export)
        self.log_export_task(export.pk, f"Creating DB '{export.target_name}', location: {db_location}")
        try:
            job_id = self.hadoop_api.create_db(name=export.target_name, location=db_location)
            self.log_export_task(export.pk, f"Received Hive DB creation job_id: {job_id}")
            export.request_job_id = job_id
            export.save()
        except (RequestException, InvalidJobId) as e:
            raise CreateHiveDBException(f"Error getting Hive DB creation job ID: {e}")

        job_status = self.track_job(export=export, job_type=APIJobType.HIVE_DB_CREATE)
        if job_status != JobStatus.finished:
            raise CreateHiveDBException("Error creating Hive DB. Check the external API for logs")
        self.log_export_task(export.pk, f"Hive DB `{export.target_name}` created.")

    def change_db_ownership(self, export: Export, db_user: str) -> None:
        try:
            self.hadoop_api.change_db_ownership(location=self.get_db_location(export=export), db_user=db_user)
            self.log_export_task(export.pk, f"`{db_user}` granted rights on DB `{export.target_name}`")
        except RequestException as e:
            raise HiveDBOwnershipException(f"Error granting `{db_user}` rights on DB `{export.target_name}` - {e}")
