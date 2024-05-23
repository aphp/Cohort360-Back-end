import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from cohort.models import DatedMeasure, CohortResult, FeasibilityStudy
from cohort.models.dated_measure import GLOBAL_DM_MODE


_logger = logging.getLogger('info')


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


