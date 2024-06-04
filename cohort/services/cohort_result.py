import json
import logging
from smtplib import SMTPException
from typing import Tuple

from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction

from admin_cohort.types import JobStatus, ServerError
from cohort.models import CohortResult, DatedMeasure, RequestQuerySnapshot, FhirFilter
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.job_server_api import job_server_status_mapper
from cohort.services.misc import get_authorization_header
from cohort.services.emails import send_email_notif_about_large_cohort
from cohort.services.ws_event_manager import ws_send_to_client
from cohort.tasks import count_cohort_task, create_cohort_task

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
                 "resourceType": fhir_filter.fhir_resource,
                 "sourcePopulation": {"caresiteCohortList": [cohort_source_id]},
                 "request": {"_id": 0,
                             "_type": "basicResource",
                             "isInclusive": True,
                             "filterFhir": fhir_filter.filter,
                             "resourceType": fhir_filter.fhir_resource
                             }
                 }
        return json.dumps(query)

    @staticmethod
    def create_cohort_subset(http_request, owner_id: str, table_name: str, source_cohort: CohortResult, fhir_filter_id: str) -> CohortResult:

        def copy_dated_measure(dm: DatedMeasure) -> DatedMeasure:
            return DatedMeasure.objects.create(mode=dm.mode,
                                               owner=dm.owner,
                                               request_query_snapshot=dm.request_query_snapshot,
                                               measure=dm.measure)

        new_dm = copy_dated_measure(source_cohort.dated_measure)
        cohort_subset = CohortResult.objects.create(is_subset=True,
                                                    name=f"{table_name}_{source_cohort.fhir_group_id}",
                                                    owner_id=owner_id,
                                                    dated_measure=new_dm)
        with transaction.atomic():
            query = CohortResultService.build_query(cohort_source_id=source_cohort.fhir_group_id,
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
    def process_creation_data(data: dict) -> None:
        if data.pop("global_estimate", False):
            snapshot_id = data.get("request_query_snapshot")
            snapshot = RequestQuerySnapshot.objects.get(pk=snapshot_id)
            dm_global = DatedMeasure.objects.create(owner=snapshot.owner,
                                                    request_query_snapshot=snapshot,
                                                    mode=GLOBAL_DM_MODE)
            data["dated_measure_global"] = dm_global.uuid

    @staticmethod
    def process_cohort_creation(request, cohort_uuid: str):
        cohort = CohortResult.objects.get(pk=cohort_uuid)
        auth_headers = get_authorization_header(request=request)
        if cohort.dated_measure_global:
            dm_global = cohort.dated_measure_global
            try:
                count_cohort_task.s(auth_headers=auth_headers,
                                    json_query=cohort.request_query_snapshot.serialized_query,
                                    dm_uuid=dm_global.uuid)\
                              .apply_async()
            except Exception as e:
                dm_global.request_job_fail_msg = f"ERROR: Could not launch cohort global count: {e}"
                dm_global.request_job_status = JobStatus.failed
                dm_global.save()
        try:
            create_cohort_task.delay(auth_headers,
                                     cohort.request_query_snapshot.serialized_query,
                                     cohort_uuid)
        except Exception as e:
            cohort.delete()
            raise ServerError("INTERNAL ERROR: Could not launch cohort creation") from e

    def process_patch_data(self, cohort: CohortResult, data: dict) -> Tuple[bool, bool]:
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
            data["fhir_group_id"] = data.pop(GROUP_ID)
        if GROUP_COUNT in data:
            cohort.dated_measure.measure = data.pop(GROUP_COUNT)
            cohort.dated_measure.save()
        return is_update_from_sjs, is_update_from_etl

    def mark_cohort_as_failed(self, cohort: CohortResult, reason: str) -> None:
        cohort.request_job_status = JobStatus.failed
        cohort.request_job_fail_msg = reason
        cohort.save()
        self.ws_send_to_client(cohort=cohort, extra_info={"error": f"Cohort failed: {reason}"})

    def ws_push_to_client(self, cohort: CohortResult) -> None:
        cohort.refresh_from_db()
        global_dm = cohort.dated_measure_global
        extra_info = {'fhir_group_id': cohort.fhir_group_id}
        if global_dm:
            extra_info['global'] = {'measure_min': global_dm.measure_min,
                                    'measure_max': global_dm.measure_max
                                    }
        self.ws_send_to_client(cohort=cohort, extra_info=extra_info)

    @staticmethod
    def ws_send_to_client(cohort: CohortResult, extra_info: dict) -> None:
        ws_send_to_client(instance=cohort, job_name='create', extra_info=extra_info)

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
