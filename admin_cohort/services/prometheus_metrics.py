from django.db import DatabaseError
from prometheus_client import REGISTRY, Counter, Histogram
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector

from admin_cohort.types import JobStatus

EXPORTS_TOTAL = Counter(
    "cohort360_exports_total",
    "Number of exports having reached a terminal state",
    labelnames=("status", "output_format"),
)

QUERY_EXECUTOR_REQUEST_DURATION_SECONDS = Histogram(
    "cohort360_query_executor_request_duration_seconds",
    "Duration between a query executor request and its terminal callback, by request type",
    labelnames=("request_type", "status"),
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1200, 1800, 3600, 7200, 10800, 14400, 21600),
)

STUCK_DATED_MEASURES_MARKED_FAILED = Counter(
    "cohort360_stuck_dated_measures_marked_failed_total",
    "DatedMeasures forced to `failed` by the watchdog, by the status they were stuck at",
    labelnames=("stuck_status",),
)

_ACTIVE_STATUSES = [s.value for s in JobStatus if not s.is_end_state and s != JobStatus.denied]


class JobsInProgressCollector(Collector):
    def collect(self):
        gauge = GaugeMetricFamily(
            "cohort360_jobs_in_progress",
            "Jobs in progress, grouped by type",
            labels=["type"],
        )
        try:
            from cohort.models import CohortResult, DatedMeasure
            from exports.models import Export

            gauge.add_metric(
                ["cohort_generation"],
                CohortResult.objects.filter(request_job_status__in=_ACTIVE_STATUSES).count(),
            )
            gauge.add_metric(
                ["count"],
                DatedMeasure.objects.filter(request_job_status__in=_ACTIVE_STATUSES).count(),
            )
            gauge.add_metric(
                ["export"],
                Export.objects.filter(request_job_status__in=_ACTIVE_STATUSES).count(),
            )
        except DatabaseError:
            pass
        yield gauge


_collector_registered = False


def register_collectors():
    global _collector_registered
    if _collector_registered:
        return
    REGISTRY.register(JobsInProgressCollector())
    _collector_registered = True
