import os

import prometheus_client
from django.http import HttpResponse
from prometheus_client import multiprocess

from admin_cohort.services.prometheus_metrics import JobsInProgressCollector


def metrics_view(request):
    multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if multiproc_dir and os.path.isdir(multiproc_dir):
        registry = prometheus_client.CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        registry.register(JobsInProgressCollector())
    else:
        registry = prometheus_client.REGISTRY
    return HttpResponse(prometheus_client.generate_latest(registry), content_type=prometheus_client.CONTENT_TYPE_LATEST)
