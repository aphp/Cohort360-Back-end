import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from admin_cohort.types import ServerError
from cohort.models import DatedMeasure, CohortResult
from cohort.models.dated_measure import GLOBAL_DM_MODE
from cohort.services.misc import get_authorization_header
from cohort.tasks import create_cohort_task

_logger = logging.getLogger('info')


def load_operator(op_type: str):
    for exporter_conf in settings.COHORT_OPERATORS:
        try:
            operator_type, cls_path = exporter_conf["TYPE"], exporter_conf["OPERATOR_CLASS"]
        except KeyError:
            raise ImproperlyConfigured("Missing `TYPE` or `OPERATOR_CLASS` key in operators configuration")
        if operator_type == op_type:
            operator = import_string(cls_path)
            if operator:
                return operator
    raise ImproperlyConfigured(f"No cohort operator of type `{op_type}` is configured")


class CohortManager:

    @staticmethod
    def get_auth_headers(request) -> dict:
        return get_authorization_header(request=request)


class CohortCountManager(CohortManager):
    OP_TYPE = "count"

    def __init__(self):
        self.operator = load_operator(op_type=self.OP_TYPE)

    def handle_global_estimate(self, cohort: CohortResult, request):
        dm_global = DatedMeasure.objects.create(mode=GLOBAL_DM_MODE,
                                                owner=request.user,
                                                request_query_snapshot_id=request.data.get("request_query_snapshot"))
        cohort.dated_measure_global = dm_global
        cohort.save()
        self.operator.launch_global_estimate(cohort, request)


class CohortCreateManager(CohortManager):

    def launch_cohort_creation(self, cohort: CohortResult, request):
        try:
            create_cohort_task.delay(self.get_auth_headers(request),
                                     cohort.request_query_snapshot.serialized_query,
                                     cohort.pk)

        except Exception as e:
            cohort.delete()
            raise ServerError("INTERNAL ERROR: Could not launch cohort creation") from e

