import logging
from smtplib import SMTPException

from django.db.models import QuerySet
from django.http import Http404
from django.utils import timezone

from accesses.models import get_user_valid_manual_accesses
from admin_cohort.models import User
from admin_cohort.types import JobStatus
from cohort.models import CohortResult
from cohort.services.conf_cohort_job_api import fhir_to_job_status
from cohort.tools import get_dict_cohort_pop_source, get_all_cohorts_rights, send_email_notif_about_large_cohort

JOB_STATUS = "request_job_status"
GROUP_ID = "group.id"
GROUP_COUNT = "group.count"

_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')


class CohortResultService:

    @staticmethod
    def count_active_jobs():
        active_statuses = [JobStatus.new,
                           JobStatus.validated,
                           JobStatus.started,
                           JobStatus.pending,
                           JobStatus.long_pending]
        return CohortResult.objects.filter(request_job_status__in=active_statuses)\
                                   .count()

    @staticmethod
    def get_cohorts_rights(cohorts: QuerySet, user: User):
        if not cohorts:
            raise Http404("ERROR: No cohorts found")
        user_accesses = get_user_valid_manual_accesses(user=user)
        if not user_accesses:
            raise Http404("ERROR: No accesses found")
        list_cohort_id = [cohort.fhir_group_id for cohort in cohorts if cohort.fhir_group_id]
        cohort_dict_pop_source = get_dict_cohort_pop_source(list_cohort_id)
        return get_all_cohorts_rights(user_accesses, cohort_dict_pop_source)

    @staticmethod
    def process_patch_data(cohort: CohortResult, data: dict) -> tuple[bool, bool]:
        _logger.info(f"Received data for cohort patch: {data}")
        sjs_data_keys = (JOB_STATUS, GROUP_ID, GROUP_COUNT)
        is_update_from_sjs = all([key in data for key in sjs_data_keys])
        is_update_from_etl = JOB_STATUS in data and len(data) == 1

        if JOB_STATUS in data:
            job_status = fhir_to_job_status().get(data[JOB_STATUS].upper())
            if not job_status:
                raise ValueError(f"Bad Request: Invalid job status: {data.get(JOB_STATUS)}")
            if job_status in (JobStatus.finished, JobStatus.failed):
                data["request_job_duration"] = str(timezone.now() - cohort.created_at)
                if job_status == JobStatus.failed:
                    data["request_job_fail_msg"] = "Received a failed status from SJS"
            data['request_job_status'] = job_status
        if GROUP_ID in data:
            data["fhir_group_id"] = data.pop(GROUP_ID)
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
                send_email_notif_about_large_cohort(cohort.name, cohort.fhir_group_id, cohort.owner)
            except (ValueError, SMTPException) as e:
                _logger_err.exception(f"Cohort [{cohort.uuid}] - Couldn't send email to user after ETL patch: {e}")
            else:
                _logger.info(f"Cohort [{cohort.uuid}] successfully updated from ETL")


cohort_service = CohortResultService()
