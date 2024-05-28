import logging
from smtplib import SMTPException

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from cohort.models import DatedMeasure, CohortResult, FeasibilityStudy
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.services.emails import send_email_notif_about_large_cohort
from exports.services.export import export_service

JOB_STATUS = "request_job_status"
GROUP_ID = "group.id"
GROUP_COUNT = "group.count"

_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')


def load_operator(job_type: str):
    for exporter_conf in settings.COHORT_OPERATORS:
        try:
            operator_type, cls_path = exporter_conf["TYPE"], exporter_conf["OPERATOR_CLASS"]
        except KeyError:
            raise ImproperlyConfigured("Missing `TYPE` or `OPERATOR_CLASS` key in operators configuration")
        if operator_type == job_type:
            operator = import_string(cls_path)
            if operator:
                return operator
    raise ImproperlyConfigured(f"No cohort operator of type `{job_type}` is configured")


class CohortManager:
    job_type = None

    def __init__(self):
        self.operator = load_operator(job_type=self.job_type)


class CohortCountManager(CohortManager):
    job_type = "count"

    def handle_count(self, dm: DatedMeasure, request) -> None:
        self.operator.launch_count(dm, request)

    def handle_global_count(self, cohort: CohortResult, request) -> None:
        dm_global = DatedMeasure.objects.create(mode=GLOBAL_DM_MODE,
                                                owner=request.user,
                                                request_query_snapshot_id=request.data.get("request_query_snapshot"))
        cohort.dated_measure_global = dm_global
        cohort.save()
        self.operator.launch_global_count(cohort, request)

    def handle_feasibility_study_count(self, fs: FeasibilityStudy, request) -> None:
        self.operator.launch_feasibility_study_count(fs, request)


class CohortCreationManager(CohortManager):
    job_type = "create"

    def handle_cohort_creation(self, cohort: CohortResult, request) -> None:
        self.operator.launch_cohort_creation(cohort, request)

    def handle_patch_data(self, cohort: CohortResult, data: dict) -> None:
        self.operator.handle_patch_data(cohort, data)

    def handle_cohort_post_update(self, cohort: CohortResult, data: dict) -> None:
        job_server_data_keys = (JOB_STATUS, GROUP_ID, GROUP_COUNT)
        is_update_from_job_server = all([key in data for key in job_server_data_keys])
        is_update_from_etl = JOB_STATUS in data and len(data) == 1

        if is_update_from_job_server:
            _logger.info(f"Cohort [{cohort.uuid}] successfully updated from Job Server")
            if cohort.export_table.exists():
                export_service.check_all_cohort_subsets_created(export=cohort.export_table.first().export)
        if is_update_from_etl:
            self.send_email_notification(cohort=cohort)

    @staticmethod
    def send_email_notification(cohort: CohortResult) -> None:
        try:
            send_email_notif_about_large_cohort(cohort.name, cohort.group_id, cohort.owner)
        except (ValueError, SMTPException) as e:
            _logger_err.exception(f"Cohort[{cohort.uuid}]: Couldn't send email to user after ETL patch: {e}")
        else:
            _logger.info(f"Cohort[{cohort.uuid}]: Successfully updated from ETL")



