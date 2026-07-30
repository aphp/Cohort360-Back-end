import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional

import certifi
import requests
from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.db import connections
from rest_framework import status


_logger = logging.getLogger(__name__)

CHECK_TIMEOUT_SECONDS = 2.0
GLOBAL_TIMEOUT_SECONDS = CHECK_TIMEOUT_SECONDS + 1.0

FHIR_CACHE_KEY = "health:fhir"
FHIR_CACHE_TTL_SECONDS = 300

_HTTP_HARD_FAIL_CODES = {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}


def _http_reachable(url: str, *, method: str = "GET", **kwargs) -> requests.Response:
    """Perform an HTTP call and treat any 5xx, 401, 403 or transport error as a failure.

    4xx (other than auth) is considered "service is up and recognised our request shape".
    """
    response = requests.request(method=method, url=url, timeout=CHECK_TIMEOUT_SECONDS, **kwargs)
    if response.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR or response.status_code in _HTTP_HARD_FAIL_CODES:
        raise RuntimeError(f"HTTP {response.status_code}")
    return response


def _check_django() -> None:
    return None


def _check_db_default() -> None:
    with connections["default"].cursor() as cursor:
        cursor.execute("SELECT 1")


def _check_redis() -> Optional[str]:
    backend = settings.CACHES["default"]["BACKEND"]
    if "RedisCache" not in backend:
        return "skipped"
    from django_redis import get_redis_connection

    get_redis_connection("default").ping()
    return None


def _check_query_executor() -> Optional[str]:
    url = os.environ.get("QUERY_EXECUTOR_URL")
    if not url:
        return "skipped"
    _http_reachable(f"{url.rstrip('/')}/jobs")
    return None


def _check_oidc() -> Optional[str]:
    if not settings.ENABLE_OIDC_AUTH:
        return "skipped"
    from admin_cohort.services.auth import build_oidc_configs

    configs = build_oidc_configs()
    if not configs:
        return "skipped"
    errors = []
    for conf in configs:
        url = f"{conf.issuer}/.well-known/openid-configuration"
        try:
            _http_reachable(url)
        except Exception as exc:
            errors.append(f"{conf.issuer}: {exc}")
    if errors:
        raise RuntimeError("; ".join(errors))
    return None


def _check_identity_server() -> Optional[str]:
    url = os.environ.get("IDENTITY_SERVER_URL")
    if not url:
        return "skipped"
    token = os.environ.get("IDENTITY_SERVER_AUTH_TOKEN", "")
    _http_reachable(
        f"{url.rstrip('/')}/user/info",
        method="POST",
        data={"username": "_healthcheck_"},
        headers={"Key-auth": token},
    )
    return None


def _check_hadoop_api() -> Optional[str]:
    if not apps.is_installed("exporters"):
        return "skipped"
    base = os.environ.get("HADOOP_API_URL")
    if not base:
        return "skipped"
    _http_reachable(
        f"{base.rstrip('/')}/hadoop/task_status",
        params={"task_uuid": "_healthcheck_"},
        headers={"auth-token": os.environ.get("HADOOP_API_AUTH_TOKEN", "")},
    )
    return None


def _check_export_api() -> Optional[str]:
    if not apps.is_installed("exporters"):
        return "skipped"
    base = os.environ.get("EXPORT_API_URL")
    if not base:
        return "skipped"
    _http_reachable(
        f"{base.rstrip('/')}/task_status",
        params={"task_uuid": "_healthcheck_"},
        headers={"auth-token": os.environ.get("EXPORT_API_AUTH_TOKEN", "")},
    )
    return None


def _check_smtp() -> Optional[str]:
    if not settings.EMAIL_HOST:
        return "skipped"
    from django.core.mail import get_connection

    conn = get_connection()
    conn.timeout = CHECK_TIMEOUT_SECONDS
    conn.open()
    conn.close()
    return None


def _check_influxdb() -> Optional[str]:
    if not settings.INFLUXDB_ENABLED:
        return "skipped"
    from influxdb_client import InfluxDBClient

    client = InfluxDBClient(
        url=settings.INFLUXDB_URL,
        token=settings.INFLUXDB_TOKEN,
        org=settings.INFLUXDB_ORG,
        ssl_ca_cert=certifi.where(),
        timeout=int(CHECK_TIMEOUT_SECONDS * 1000),
    )
    try:
        if not client.ping():
            raise RuntimeError("ping returned false")
    finally:
        client.close()
    return None


def _check_fhir() -> Optional[str]:
    fhir_url = os.environ.get("FHIR_URL")
    if not fhir_url:
        return "skipped"
    cached = cache.get(FHIR_CACHE_KEY)
    if cached is not None:
        if cached.get("ok"):
            return None
        raise RuntimeError(cached.get("error") or "cached failure")
    try:
        response = _http_reachable(
            f"{fhir_url.rstrip('/')}/metadata",
            headers={"Accept": "application/fhir+json"},
        )
        resource_type = response.json().get("resourceType")
        if resource_type != "CapabilityStatement":
            raise RuntimeError(f"unexpected resourceType: {resource_type!r}")
    except Exception as exc:
        cache.set(FHIR_CACHE_KEY, {"ok": False, "error": str(exc)[:300]}, FHIR_CACHE_TTL_SECONDS)
        raise
    cache.set(FHIR_CACHE_KEY, {"ok": True, "error": None}, FHIR_CACHE_TTL_SECONDS)
    return None


CHECKS: list[tuple[str, Callable[[], Optional[str]], bool]] = [
    ("django", _check_django, True),
    ("db_default", _check_db_default, True),
    ("redis", _check_redis, True),
    ("query_executor", _check_query_executor, False),
    ("oidc", _check_oidc, False),
    ("identity_server", _check_identity_server, False),
    ("hadoop_api", _check_hadoop_api, False),
    ("export_api", _check_export_api, False),
    ("smtp", _check_smtp, False),
    ("influxdb", _check_influxdb, False),
    ("fhir", _check_fhir, False),
]


def _run_check(fn: Callable[[], Optional[str]], critical: bool) -> dict:
    start = time.monotonic()
    skipped = False
    ok = True
    error: Optional[str] = None
    try:
        result = fn()
        if result == "skipped":
            skipped = True
    except Exception as exc:
        ok = False
        error = str(exc)[:300] or exc.__class__.__name__
    finally:
        # close any thread-local DB connection opened inside the worker
        connections.close_all()
    return {
        "ok": ok if not skipped else True,
        "skipped": skipped,
        "critical": critical,
        "duration_ms": int((time.monotonic() - start) * 1000),
        "error": error,
    }


def run_health_checks() -> dict:
    results: dict[str, dict] = {}
    pending: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=len(CHECKS)) as executor:
        future_to_name = {executor.submit(_run_check, fn, critical): (name, critical) for name, fn, critical in CHECKS}
        try:
            for future in as_completed(future_to_name, timeout=GLOBAL_TIMEOUT_SECONDS):
                name, _ = future_to_name[future]
                results[name] = future.result()
        except TimeoutError:
            pass
        for future, (name, critical) in future_to_name.items():
            if name in results:
                continue
            pending[name] = {
                "ok": False,
                "skipped": False,
                "critical": critical,
                "duration_ms": int(GLOBAL_TIMEOUT_SECONDS * 1000),
                "error": "timeout",
            }
            future.cancel()
    results.update(pending)

    has_critical_ko = any(c["critical"] and not c["ok"] for c in results.values())
    has_any_ko = any(not c["ok"] for c in results.values())
    if has_critical_ko:
        global_status = "ko"
    elif has_any_ko:
        global_status = "degraded"
    else:
        global_status = "ok"

    return {
        "status": global_status,
        "version": settings.VERSION,
        "checks": results,
    }
