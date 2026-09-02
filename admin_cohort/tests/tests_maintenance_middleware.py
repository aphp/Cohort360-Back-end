import json
import os
from datetime import datetime as dt, timedelta, UTC
from unittest.mock import MagicMock, patch

from rest_framework import status
from rest_framework.test import APIRequestFactory

from admin_cohort import settings
from admin_cohort.middleware.maintenance_middleware import MaintenanceModeMiddleware
from admin_cohort.services.auth import JWTAuth
from .tests_tools import TestCaseWithDBs
from ..models import MaintenancePhase
from ..models.maintenance import MaintenanceType

env = os.environ

EXEMPTED_USER = "exempted_user"


def enable_maintenance(minutes=5, maintenance_type=MaintenanceType.PARTIAL):
    data = dict(
        subject="maintenance for middleware testing",
        type=maintenance_type,
        start_datetime=dt.now(UTC),
        end_datetime=dt.now(UTC) + timedelta(minutes=minutes),
    )
    MaintenancePhase.objects.create(**data)


class MaintenanceModeMiddlewareTests(TestCaseWithDBs):
    def setUp(self):
        get_response = MagicMock()
        self.middleware = MaintenanceModeMiddleware(get_response)
        self.factory = APIRequestFactory()

        self.safe_method_url = "/accesses/roles/"
        self.non_safe_method_url = "/accesses/roles/"
        self.query_executor_etl_callback_url = "/cohort/cohorts/"
        self.maintenance_url = "/maintenances/"
        self.auth_url = "/auth/"

        enable_maintenance(5)

    def test_safe_method_request(self):
        request = self.factory.get(path=self.safe_method_url)
        response = self.middleware(request)
        self.assertNotEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_non_safe_method_request(self):
        request = self.factory.post(path=self.non_safe_method_url, data={"name": "New role with no rights"})
        response = self.middleware(request)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("maintenance_start", content)
        self.assertIn("maintenance_end", content)
        self.assertIn("message", content)
        self.assertTrue(content.get("active"))

    def test_query_executor_etl_callback_request(self):
        request = self.factory.patch(path=self.query_executor_etl_callback_url + "some_cohort_uuid/", data={"request_job_status": "finished"})
        request.META = {"HTTP_AUTHORIZATION": f"Bearer {env.get('QUERY_EXECUTOR_TOKEN')}"}
        response = self.middleware(request)
        self.assertNotEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_maintenance_request(self):
        request = self.factory.post(path=self.maintenance_url, data={})
        response = self.middleware(request)
        self.assertNotEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_accounts_request(self):
        request = self.factory.post(path=self.auth_url, data={})
        response = self.middleware(request)
        self.assertNotEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def non_safe_authenticated_request(self):
        request = self.factory.post(path=self.non_safe_method_url, data={"name": "New role with no rights"})
        request.META.update({"HTTP_AUTHORIZATION": "Bearer some_token", f"HTTP_{settings.AUTHORIZATION_METHOD_HEADER}": settings.JWT_AUTH_MODE})
        return request

    @patch.object(settings, "MAINTENANCE_EXEMPTED_USERS", [EXEMPTED_USER])
    @patch.object(JWTAuth, "decode_token", return_value={"username": EXEMPTED_USER})
    def test_non_safe_method_request_by_exempted_user(self, mock_decode_token):
        response = self.middleware(self.non_safe_authenticated_request())
        self.assertNotEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        mock_decode_token.assert_called()

    @patch.object(settings, "MAINTENANCE_EXEMPTED_USERS", [EXEMPTED_USER])
    @patch.object(JWTAuth, "decode_token", return_value={"username": "some_other_user"})
    def test_non_safe_method_request_by_non_exempted_user(self, mock_decode_token):
        response = self.middleware(self.non_safe_authenticated_request())
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch.object(settings, "MAINTENANCE_EXEMPTED_USERS", [EXEMPTED_USER])
    @patch.object(JWTAuth, "decode_token", return_value={"username": EXEMPTED_USER})
    def test_non_safe_method_request_by_exempted_user_during_full_maintenance(self, mock_decode_token):
        MaintenancePhase.objects.all().delete()
        enable_maintenance(maintenance_type=MaintenanceType.FULL)
        response = self.middleware(self.non_safe_authenticated_request())
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
