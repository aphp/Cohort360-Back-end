import logging
from typing import List

from requests import RequestException

from admin_cohort.models import User
from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from exports.models import Export, Datalab
from exporters.exporters.base_exporter import BaseExporter
from exporters.enums import ExportTypes, APIJobType

logger = logging.getLogger(__name__)


class HiveExporter(BaseExporter):
    def __init__(self):
        super().__init__()
        self.type = ExportTypes.HIVE.value
        self.target_location = self.hadoop_api.hive_db_path
        self.user = self.hadoop_api.hive_user

    def validate(self, export_data: dict, **kwargs) -> None:
        self.validate_tables_data(tables_data=export_data.get("export_tables", []))
        kwargs["source_cohorts_ids"] = [t.get("cohort_result_source") for t in export_data.get("export_tables", []) if t.get("cohort_result_source")]
        super().validate(export_data=export_data, **kwargs)

    def validate_tables_data(self, tables_data: List[dict]) -> bool:
        required_table = self.export_api.required_table
        base_cohort_provided = False
        required_table_provided = False
        for td in tables_data:
            source_cohort_id = td.get("cohort_result_source")

            if td.get("table_name", "").lower() == required_table.lower():
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

    def handle_export(self, export: Export, params: dict = None) -> None:
        logger.info(f"Export[{export.pk}] Starting Hive export process for target: {export.target_name}")
        self.confirm_export_received(export=export)
        try:
            logger.info(f"Export[{export.pk}] Preparing database...")
            self.prepare_db(export)
            logger.info(f"Export[{export.pk}] Database preparation completed successfully")
        except RequestException as e:
            logger.error(f"Export[{export.pk}] Failed to prepare database: {e}")
            self.mark_export_as_failed(export=export, reason=f"Error while preparing DB for export: {e}")
        else:
            params = params or {"output": {"type": self.type, "databaseName": export.target_name}}
            logger.info(f"Export[{export.pk}] Calling parent handle_export with params: {params}")
            # The parent runs the export job and then calls finalize_export() (overridden below) to
            # transfer ownership to the datalab before the export is reported as successful.
            super().handle_export(export=export, params=params)
            logger.info(f"Export[{export.pk}] Hive export process finished")

    def finalize_export(self, export: Export) -> None:
        logger.info(f"Export[{export.pk}] Concluding export...")
        self.conclude_export(export=export)

    def prepare_db(self, export: Export) -> None:
        logger.info(f"Export[{export.pk}] prepare_db: Creating database")
        self.create_db(export=export)
        logger.info(f"Export[{export.pk}] prepare_db: Changing database ownership to user '{self.user}'")
        self.change_db_ownership(export=export, db_user=self.user)
        logger.info(f"Export[{export.pk}] prepare_db: Database preparation steps completed")

    @staticmethod
    def get_db_location(export: Export) -> str:
        return f"{export.target_full_path}.db"

    def create_db(self, export: Export) -> None:
        logger.info(f"Export[{export.pk}] create_db: Starting database creation")
        db_location = self.get_db_location(export=export)
        logger.info(f"Export[{export.pk}] create_db: DB location resolved to '{db_location}'")
        self.log_export_task(export.pk, f"Creating DB '{export.target_name}', location: {db_location}")
        try:
            logger.info(f"Export[{export.pk}] create_db: Calling hadoop_api.create_db(name='{export.target_name}')")
            job_id = self.hadoop_api.create_db(name=export.target_name, location=db_location)
            logger.info(f"Export[{export.pk}] create_db: Received job_id='{job_id}'")
            self.log_export_task(export.pk, f"Received Hive DB creation job_id: {job_id}")
            logger.info(f"Export[{export.pk}] create_db: Waiting for job completion...")
            self.wait_for_job(export=export, job_id=job_id, job_type=APIJobType.HIVE_DB_CREATE)
            logger.info(f"Export[{export.pk}] create_db: Job completed successfully")
        except RequestException as e:
            logger.error(f"Export[{export.pk}] create_db: Error on call to create Hive DB: {e}")
            raise e
        self.log_export_task(export.pk, f"DB '{export.target_name}' created.")
        logger.info(f"Export[{export.pk}] create_db: Database '{export.target_name}' created successfully")

    def change_db_ownership(self, export: Export, db_user: str) -> None:
        try:
            self.hadoop_api.change_db_ownership(location=self.get_db_location(export=export), db_user=db_user)
            self.log_export_task(export.pk, f"`{db_user}` granted rights on DB `{export.target_name}`")
        except RequestException as e:
            raise RequestException(f"Error granting `{db_user}` rights on DB `{export.target_name}` - {e}")

    def conclude_export(self, export: Export) -> None:
        # Transfers ownership of the exported DB files to the datalab's unix account. Any failure
        # propagates so the caller (finalize_export -> base handle_export) marks the export as failed
        # instead of leaving the files owned by the technical Hive user and unreadable by the datalab.
        db_user = export.datalab.name
        self.change_db_ownership(export=export, db_user=db_user)
        self.log_export_task(export.pk, f"Export concluded: DB '{export.target_name}' attributed to {db_user}.")
