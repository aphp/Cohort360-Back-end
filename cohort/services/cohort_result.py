import json
import logging
from smtplib import SMTPException

from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction

from admin_cohort.types import JobStatus
from cohort.models import CohortResult, FhirFilter
from cohort.job_server_api import job_server_status_mapper
from cohort.services.cohort_managers import CohortCountManager, CohortCreateManager
from cohort.services.misc import get_authorization_header
from cohort.services.emails import send_email_notif_about_large_cohort
from cohort.tasks import create_cohort_task

JOB_STATUS = "request_job_status"
GROUP_ID = "group.id"
GROUP_COUNT = "group.count"

_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')


class CohortResultService:

    @staticmethod
    def build_query(cohort_source_id: str, fhir_filter_id: str) -> str:
        fhir_filter = FhirFilter.objects.get(pk=fhir_filter_id)
        query = {"_type": "request",
                 "sourcePopulation": {"caresiteCohortList": [cohort_source_id]},
                 "request": {"_id": 0,
                             "_type": "andGroup",
                             "isInclusive": True,
                             "criteria": [{"_id": 1,
                                           "_type": "basicResource",
                                           "isInclusive": True,
                                           "filterFhir": fhir_filter.filter,
                                           "resourceType": fhir_filter.fhir_resource
                                           }]
                             }
                 }
        return json.dumps(query)

    @staticmethod
    def create_cohort_subset(http_request, owner_id: str, table_name: str, source_cohort: CohortResult, fhir_filter_id: str) -> CohortResult:
        cohort_subset = CohortResult.objects.create(is_subset=True,
                                                    name=f"{table_name}_{source_cohort.group_id}",
                                                    owner_id=owner_id,
                                                    dated_measure_id=source_cohort.dated_measure_id)
        with transaction.atomic():
            query = CohortResultService.build_query(cohort_source_id=source_cohort.group_id,
                                                    fhir_filter_id=fhir_filter_id)
            try:
                auth_headers = get_authorization_header(request=http_request)
                create_cohort_task.delay(auth_headers,
                                         query,
                                         cohort_subset.uuid)
            except Exception as e:
                cohort_subset.delete()
                raise ValidationError(f"Error creating the cohort subset for export: {e}")
        return cohort_subset

    @staticmethod
    def count_active_jobs():
        active_statuses = [JobStatus.new,
                           JobStatus.validated,
                           JobStatus.started,
                           JobStatus.pending]
        return CohortResult.objects.filter(request_job_status__in=active_statuses)\
                                   .count()

    @staticmethod
    def proceed_with_cohort_creation(request, cohort: CohortResult):
        if request.data.pop("global_estimate", False):
            CohortCountManager().handle_global_estimate(cohort, request)
        CohortCreateManager().launch_cohort_creation(cohort, request)

    @staticmethod
    def process_patch_data(cohort: CohortResult, data: dict) -> tuple[bool, bool]:
        _logger.info(f"Received data for cohort patch: {data}")
        sjs_data_keys = (JOB_STATUS, GROUP_ID, GROUP_COUNT)
        is_update_from_sjs = all([key in data for key in sjs_data_keys])
        is_update_from_etl = JOB_STATUS in data and len(data) == 1

        if JOB_STATUS in data:
            job_status = job_server_status_mapper(data[JOB_STATUS])
            if not job_status:
                raise ValueError(f"Bad Request: Invalid job status: {data.get(JOB_STATUS)}")
            if job_status in (JobStatus.finished, JobStatus.failed):
                data["request_job_duration"] = str(timezone.now() - cohort.created_at)
                if job_status == JobStatus.failed:
                    data["request_job_fail_msg"] = "Received a failed status from SJS"
            data['request_job_status'] = job_status
        if GROUP_ID in data:
            data["group_id"] = data.pop(GROUP_ID)
        if GROUP_COUNT in data:
            cohort.dated_measure.measure = data.pop(GROUP_COUNT)
            cohort.dated_measure.save()
        return is_update_from_sjs, is_update_from_etl

    @staticmethod
    def send_email_notification(cohort: CohortResult, is_update_from_sjs: bool, is_update_from_etl: bool) -> None:
        if is_update_from_sjs:
            _logger.info(f"Cohort [{cohort.uuid}] successfully updated from SJS")
        if is_update_from_etl:
            try:
                send_email_notif_about_large_cohort(cohort.name, cohort.group_id, cohort.owner)
            except (ValueError, SMTPException) as e:
                _logger_err.exception(f"Cohort [{cohort.uuid}] - Couldn't send email to user after ETL patch: {e}")
            else:
                _logger.info(f"Cohort [{cohort.uuid}] successfully updated from ETL")


cohort_service = CohortResultService()
