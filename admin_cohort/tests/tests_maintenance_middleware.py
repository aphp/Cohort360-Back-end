import json
import os
from datetime import datetime as dt, timedelta, UTC
from unittest import TestCase
from unittest.mock import MagicMock

from rest_framework import status
from rest_framework.test import APIRequestFactory

from admin_cohort.middleware.maintenance_middleware import MaintenanceModeMiddleware
from ..models import MaintenancePhase

env = os.environ


def enable_maintenance(minutes=5):
    data = dict(subject="maintenance for middleware testing",
                start_datetime=dt.now(UTC),
                end_datetime=dt.now(UTC) + timedelta(minutes=minutes))
    MaintenancePhase.objects.create(**data)


class MaintenanceModeMiddlewareTests(TestCase):

    def setUp(self):
        get_response = MagicMock()
        self.middleware = MaintenanceModeMiddleware(get_response)
        self.factory = APIRequestFactory()

        self.safe_method_url = '/accesses/roles/'
        self.non_safe_method_url = '/accesses/roles/'
        self.sjs_etl_callback_url = '/cohort/cohorts/'
        self.maintenance_url = '/maintenances/'
        self.auth_url = '/auth/'

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
        self.assertIn('maintenance_start', content)
        self.assertIn('maintenance_end', content)
        self.assertIn('message', content)
        self.assertTrue(content.get('active'))

    def test_sjs_etl_callback_request(self):
        request = self.factory.patch(path=self.sjs_etl_callback_url+'some_cohort_uuid/',
                                     data={"request_job_status": "finished"})
        request.META = {"HTTP_AUTHORIZATION": f"Bearer {env.get('SJS_TOKEN')}"}
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
