import logging
from typing import Tuple

from celery import chain
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string
from rest_framework.request import Request

from admin_cohort.middleware.request_trace_id_middleware import add_trace_id
from admin_cohort.types import JobStatus
from cohort.models import DatedMeasure, CohortResult, FeasibilityStudy
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.services.misc import ServerError
from cohort.tasks import create_cohort, cancel_previous_count_jobs, count_cohort, feasibility_study_count, send_feasibility_study_notification

_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')


def get_authorization_header(request: Request) -> dict:
    headers = {"Authorization": f"Bearer {request.META.get('HTTP_AUTHORIZATION')}",
               "authorizationMethod": request.META.get('HTTP_AUTHORIZATIONMETHOD')
               }
    headers = add_trace_id(headers)
    return headers


def load_operator(job_type: str):
    for exporter_conf in settings.COHORT_OPERATORS:
        try:
            operator_type, cls_path = exporter_conf["TYPE"], exporter_conf["OPERATOR_CLASS"]
        except KeyError:
            raise ImproperlyConfigured("Missing `TYPE` or `OPERATOR_CLASS` key in operators configuration")
        if operator_type == job_type:
            operator_cls = import_string(cls_path)
            if operator_cls:
                return operator_cls
    raise ImproperlyConfigured(f"No cohort operator of type `{job_type}` is configured")


class CohortManager:
    job_type = None

    def __init__(self):
        self.operator_cls = load_operator(job_type=self.job_type)
        self.operator = self.operator_cls()


class CohortCounter(CohortManager):
    job_type = "count"

    def handle_count(self, dm: DatedMeasure, request) -> None:
        cancel_previous_count_jobs.s(dm_uuid=dm.uuid,
                                     operator_cls=self.operator_cls) \
                                  .apply_async()
        try:
            count_cohort.s(dm_id=dm.uuid,
                           json_query=dm.request_query_snapshot.serialized_query,
                           auth_headers=get_authorization_header(request),
                           operator_cls=self.operator_cls) \
                        .apply_async()
        except Exception as e:
            dm.delete()
            raise ServerError("Could not launch count request") from e

    def handle_global_count(self, cohort: CohortResult, request) -> None:
        dm_global = DatedMeasure.objects.create(mode=GLOBAL_DM_MODE,
                                                owner=request.user,
                                                request_query_snapshot_id=request.data.get("request_query_snapshot"))
        try:
            count_cohort.s(dm_id=dm_global.uuid,
                           json_query=dm_global.request_query_snapshot.serialized_query,
                           auth_headers=get_authorization_header(request),
                           operator_cls=self.operator_cls,
                           global_estimate=True) \
                        .apply_async()
        except Exception as e:
            raise ServerError("Could not launch count request") from e
        cohort.dated_measure_global = dm_global
        cohort.save()

    def handle_feasibility_study_count(self, fs: FeasibilityStudy, request) -> None:
        try:
            chain(*(feasibility_study_count.s(fs_id=fs.uuid,
                                              json_qury=fs.request_query_snapshot.serialized_query,
                                              auth_headers=get_authorization_header(request),
                                              operator_cls=self.operator_cls),
                    send_feasibility_study_notification.s(fs.uuid)))()
        except Exception as e:
            fs.delete()
            raise ServerError("Could not launch feasibility request") from e

    def handle_patch_dated_measure(self, dm, data) -> None:
        self.operator.handle_patch_dated_measure(dm, data)

    def handle_patch_feasibility_study(self, fs, data) -> Tuple[JobStatus, dict]:
        return self.operator.handle_patch_feasibility_study(fs, data)


class CohortCreator(CohortManager):
    job_type = "create"

    def handle_cohort_creation(self, cohort: CohortResult, request) -> None:
        try:
            create_cohort.s(cohort_id=cohort.pk,
                            json_query=cohort.request_query_snapshot.serialized_query,
                            auth_headers=get_authorization_header(request),
                            operator_cls=self.operator_cls) \
                         .apply_async()

        except Exception as e:
            cohort.delete()
            raise ServerError("Could not launch cohort creation") from e

    def handle_patch_cohort(self, cohort: CohortResult, data: dict) -> None:
        self.operator.handle_patch_cohort(cohort, data)

    def handle_cohort_post_update(self, cohort: CohortResult, data: dict) -> None:
        self.operator.handle_cohort_post_update(cohort, data)
