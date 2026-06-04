import unittest
from unittest import mock
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from admin_cohort.services import health as health_module
from admin_cohort.services.health import (
    FHIR_CACHE_KEY,
    FHIR_CACHE_TTL_SECONDS,
    _check_db_default,
    _check_django,
    _check_export_api,
    _check_fhir,
    _check_hadoop_api,
    _check_identity_server,
    _check_influxdb,
    _check_oidc,
    _check_query_executor,
    _check_redis,
    _check_smtp,
    _http_reachable,
    _run_check,
    run_health_checks,
)
from admin_cohort.tools.exception_handler import custom_exception_handler


class HttpReachableTests(unittest.TestCase):
    @patch("admin_cohort.services.health.requests.request")
    def test_2xx_ok(self, mock_request):
        mock_request.return_value = MagicMock(status_code=200)
        self.assertIsNone(_http_reachable("http://x"))

    @patch("admin_cohort.services.health.requests.request")
    def test_4xx_non_auth_is_ok(self, mock_request):
        mock_request.return_value = MagicMock(status_code=404)
        self.assertIsNone(_http_reachable("http://x"))

    @patch("admin_cohort.services.health.requests.request")
    def test_500_raises(self, mock_request):
        mock_request.return_value = MagicMock(status_code=500)
        with self.assertRaises(RuntimeError):
            _http_reachable("http://x")

    @patch("admin_cohort.services.health.requests.request")
    def test_401_raises(self, mock_request):
        mock_request.return_value = MagicMock(status_code=401)
        with self.assertRaises(RuntimeError):
            _http_reachable("http://x")

    @patch("admin_cohort.services.health.requests.request")
    def test_403_raises(self, mock_request):
        mock_request.return_value = MagicMock(status_code=403)
        with self.assertRaises(RuntimeError):
            _http_reachable("http://x")


class CheckDbDefaultTests(TestCase):
    databases = {"default"}

    def test_check_db_default_runs_query(self):
        self.assertIsNone(_check_db_default())


class IndividualChecksTests(SimpleTestCase):
    def test_check_django_returns_none(self):
        self.assertIsNone(_check_django())

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_check_redis_skipped_when_not_redis(self):
        self.assertEqual(_check_redis(), "skipped")

    @patch.dict("os.environ", {}, clear=False)
    def test_check_query_executor_skipped_when_no_url(self):
        with patch.dict("os.environ", {"QUERY_EXECUTOR_URL": ""}):
            self.assertEqual(_check_query_executor(), "skipped")

    @patch("admin_cohort.services.health._http_reachable")
    def test_check_query_executor_calls_http(self, mock_http):
        with patch.dict("os.environ", {"QUERY_EXECUTOR_URL": "http://qe/"}):
            self.assertIsNone(_check_query_executor())
        mock_http.assert_called_once_with("http://qe/jobs")

    @override_settings(ENABLE_OIDC_AUTH=False)
    def test_check_oidc_skipped_when_disabled(self):
        self.assertEqual(_check_oidc(), "skipped")

    @override_settings(ENABLE_OIDC_AUTH=True)
    @patch("admin_cohort.services.auth.build_oidc_configs", return_value=[])
    def test_check_oidc_skipped_when_no_config(self, _):
        self.assertEqual(_check_oidc(), "skipped")

    @override_settings(ENABLE_OIDC_AUTH=True)
    @patch("admin_cohort.services.health._http_reachable")
    @patch("admin_cohort.services.auth.build_oidc_configs")
    def test_check_oidc_success(self, mock_configs, mock_http):
        mock_configs.return_value = [MagicMock(issuer="http://oidc")]
        self.assertIsNone(_check_oidc())
        mock_http.assert_called_once_with("http://oidc/.well-known/openid-configuration")

    @override_settings(ENABLE_OIDC_AUTH=True)
    @patch("admin_cohort.services.health._http_reachable", side_effect=RuntimeError("HTTP 500"))
    @patch("admin_cohort.services.auth.build_oidc_configs")
    def test_check_oidc_raises_on_failure(self, mock_configs, _):
        mock_configs.return_value = [MagicMock(issuer="http://oidc")]
        with self.assertRaises(RuntimeError):
            _check_oidc()

    def test_check_identity_server_skipped_when_no_url(self):
        with patch.dict("os.environ", {"IDENTITY_SERVER_URL": ""}):
            self.assertEqual(_check_identity_server(), "skipped")

    @patch("admin_cohort.services.health._http_reachable")
    def test_check_identity_server_calls_http(self, mock_http):
        with patch.dict("os.environ", {"IDENTITY_SERVER_URL": "http://id/", "IDENTITY_SERVER_AUTH_TOKEN": "tok"}):
            self.assertIsNone(_check_identity_server())
        mock_http.assert_called_once()

    @patch("admin_cohort.services.health.apps.is_installed", return_value=False)
    def test_check_hadoop_api_skipped_when_app_missing(self, _):
        self.assertEqual(_check_hadoop_api(), "skipped")

    @patch("admin_cohort.services.health.apps.is_installed", return_value=True)
    def test_check_hadoop_api_skipped_when_no_url(self, _):
        with patch.dict("os.environ", {"HADOOP_API_URL": ""}):
            self.assertEqual(_check_hadoop_api(), "skipped")

    @patch("admin_cohort.services.health.apps.is_installed", return_value=True)
    @patch("admin_cohort.services.health._http_reachable")
    def test_check_hadoop_api_calls_http(self, mock_http, _):
        with patch.dict("os.environ", {"HADOOP_API_URL": "http://h/", "HADOOP_API_AUTH_TOKEN": "tok"}):
            self.assertIsNone(_check_hadoop_api())
        mock_http.assert_called_once()

    @patch("admin_cohort.services.health.apps.is_installed", return_value=False)
    def test_check_export_api_skipped_when_app_missing(self, _):
        self.assertEqual(_check_export_api(), "skipped")

    @patch("admin_cohort.services.health.apps.is_installed", return_value=True)
    def test_check_export_api_skipped_when_no_url(self, _):
        with patch.dict("os.environ", {"EXPORT_API_URL": ""}):
            self.assertEqual(_check_export_api(), "skipped")

    @patch("admin_cohort.services.health.apps.is_installed", return_value=True)
    @patch("admin_cohort.services.health._http_reachable")
    def test_check_export_api_calls_http(self, mock_http, _):
        with patch.dict("os.environ", {"EXPORT_API_URL": "http://e/", "EXPORT_API_AUTH_TOKEN": "tok"}):
            self.assertIsNone(_check_export_api())
        mock_http.assert_called_once()

    @override_settings(EMAIL_HOST="")
    def test_check_smtp_skipped_when_no_host(self):
        self.assertEqual(_check_smtp(), "skipped")

    @override_settings(EMAIL_HOST="smtp.example.com")
    @patch("django.core.mail.get_connection")
    def test_check_smtp_open_close(self, mock_get_connection):
        conn = MagicMock()
        mock_get_connection.return_value = conn
        self.assertIsNone(_check_smtp())
        conn.open.assert_called_once()
        conn.close.assert_called_once()

    @override_settings(INFLUXDB_ENABLED=False)
    def test_check_influxdb_skipped_when_disabled(self):
        self.assertEqual(_check_influxdb(), "skipped")

    @override_settings(INFLUXDB_ENABLED=True, INFLUXDB_URL="http://x", INFLUXDB_TOKEN="t", INFLUXDB_ORG="o")
    @patch("influxdb_client.InfluxDBClient")
    def test_check_influxdb_ping_ok(self, mock_client_cls):
        client = MagicMock()
        client.ping.return_value = True
        mock_client_cls.return_value = client
        self.assertIsNone(_check_influxdb())
        client.close.assert_called_once()

    @override_settings(INFLUXDB_ENABLED=True, INFLUXDB_URL="http://x", INFLUXDB_TOKEN="t", INFLUXDB_ORG="o")
    @patch("influxdb_client.InfluxDBClient")
    def test_check_influxdb_ping_false_raises(self, mock_client_cls):
        client = MagicMock()
        client.ping.return_value = False
        mock_client_cls.return_value = client
        with self.assertRaises(RuntimeError):
            _check_influxdb()
        client.close.assert_called_once()


class CheckFhirTests(SimpleTestCase):
    def test_skipped_when_no_url(self):
        with patch.dict("os.environ", {"FHIR_URL": ""}):
            self.assertEqual(_check_fhir(), "skipped")

    @patch("admin_cohort.services.health._http_reachable")
    @patch("admin_cohort.services.health.cache")
    def test_cache_hit_ok_skips_http_call(self, mock_cache, mock_http):
        mock_cache.get.return_value = {"ok": True, "error": None}
        with patch.dict("os.environ", {"FHIR_URL": "http://fhir/"}):
            self.assertIsNone(_check_fhir())
        mock_http.assert_not_called()
        mock_cache.set.assert_not_called()

    @patch("admin_cohort.services.health._http_reachable")
    @patch("admin_cohort.services.health.cache")
    def test_cache_hit_ko_raises_without_http_call(self, mock_cache, mock_http):
        mock_cache.get.return_value = {"ok": False, "error": "previous boom"}
        with patch.dict("os.environ", {"FHIR_URL": "http://fhir/"}):
            with self.assertRaises(RuntimeError) as ctx:
                _check_fhir()
        self.assertIn("previous boom", str(ctx.exception))
        mock_http.assert_not_called()
        mock_cache.set.assert_not_called()

    @patch("admin_cohort.services.health._http_reachable")
    @patch("admin_cohort.services.health.cache")
    def test_cache_miss_success_caches_ok(self, mock_cache, mock_http):
        mock_cache.get.return_value = None
        with patch.dict("os.environ", {"FHIR_URL": "http://fhir/"}):
            self.assertIsNone(_check_fhir())
        mock_http.assert_called_once_with(
            "http://fhir/metadata",
            headers={"Accept": "application/fhir+json"},
        )
        mock_cache.set.assert_called_once_with(FHIR_CACHE_KEY, {"ok": True, "error": None}, FHIR_CACHE_TTL_SECONDS)

    @patch("admin_cohort.services.health._http_reachable", side_effect=RuntimeError("HTTP 500"))
    @patch("admin_cohort.services.health.cache")
    def test_cache_miss_failure_caches_ko_and_raises(self, mock_cache, _mock_http):
        mock_cache.get.return_value = None
        with patch.dict("os.environ", {"FHIR_URL": "http://fhir/"}):
            with self.assertRaises(RuntimeError):
                _check_fhir()
        mock_cache.set.assert_called_once_with(FHIR_CACHE_KEY, {"ok": False, "error": "HTTP 500"}, FHIR_CACHE_TTL_SECONDS)


class RunCheckTests(SimpleTestCase):
    def test_run_check_success(self):
        result = _run_check(lambda: None, critical=True)
        self.assertTrue(result["ok"])
        self.assertFalse(result["skipped"])
        self.assertTrue(result["critical"])
        self.assertIsNone(result["error"])
        self.assertIn("duration_ms", result)

    def test_run_check_skipped(self):
        result = _run_check(lambda: "skipped", critical=False)
        self.assertTrue(result["ok"])
        self.assertTrue(result["skipped"])

    def test_run_check_exception(self):
        def boom():
            raise RuntimeError("boom")

        result = _run_check(boom, critical=True)
        self.assertFalse(result["ok"])
        self.assertFalse(result["skipped"])
        self.assertEqual(result["error"], "boom")


class RunHealthChecksTests(SimpleTestCase):
    def test_all_ok(self):
        fake_checks = [("a", lambda: None, True), ("b", lambda: None, False)]
        with mock.patch.object(health_module, "CHECKS", fake_checks):
            report = run_health_checks()
        self.assertEqual(report["status"], "ok")
        self.assertEqual(set(report["checks"].keys()), {"a", "b"})

    def test_non_critical_failure_is_degraded(self):
        def boom():
            raise RuntimeError("oops")

        fake_checks = [("a", lambda: None, True), ("b", boom, False)]
        with mock.patch.object(health_module, "CHECKS", fake_checks):
            report = run_health_checks()
        self.assertEqual(report["status"], "degraded")
        self.assertFalse(report["checks"]["b"]["ok"])

    def test_critical_failure_is_ko(self):
        def boom():
            raise RuntimeError("down")

        fake_checks = [("a", boom, True), ("b", lambda: None, False)]
        with mock.patch.object(health_module, "CHECKS", fake_checks):
            report = run_health_checks()
        self.assertEqual(report["status"], "ko")


class HealthViewTests(TestCase):
    databases = {"default"}

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("health")

    @patch("admin_cohort.views.health.run_health_checks")
    def test_view_returns_200_on_ok(self, mock_run):
        mock_run.return_value = {"status": "ok", "version": "x", "checks": {}}
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "ok")

    @patch("admin_cohort.views.health.run_health_checks")
    def test_view_returns_200_on_degraded(self, mock_run):
        mock_run.return_value = {"status": "degraded", "version": "x", "checks": {}}
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("admin_cohort.views.health.run_health_checks")
    def test_view_returns_503_on_ko(self, mock_run):
        mock_run.return_value = {"status": "ko", "version": "x", "checks": {}}
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)


class CustomExceptionHandlerTests(unittest.TestCase):
    @patch("admin_cohort.tools.exception_handler.logger")
    @patch("admin_cohort.tools.exception_handler.exception_handler")
    def test_logs_and_returns_drf_response(self, mock_drf_handler, mock_logger):
        sentinel = MagicMock()
        mock_drf_handler.return_value = sentinel
        view = MagicMock()
        view.__class__.__name__ = "SomeView"
        request = MagicMock(user="alice", method="GET", path="/x")
        exc = ValueError("nope")

        result = custom_exception_handler(exc, {"view": view, "request": request})

        self.assertIs(result, sentinel)
        mock_logger.error.assert_called_once()

    @patch("admin_cohort.tools.exception_handler.logger")
    @patch("admin_cohort.tools.exception_handler.exception_handler", return_value=None)
    def test_handles_missing_view_and_request(self, _mock_drf, mock_logger):
        custom_exception_handler(ValueError("x"), {})
        mock_logger.error.assert_called_once()
