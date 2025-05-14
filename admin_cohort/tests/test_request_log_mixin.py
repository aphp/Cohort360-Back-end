from unittest import mock
from unittest.mock import MagicMock

from django.conf import settings
from rest_framework import status
from rest_framework_tracking.models import APIRequestLog

from admin_cohort.tests.tests_auth import create_regular_user
from admin_cohort.tests.tests_tools import TestCaseWithDBs


class RequestLogMixinTests(TestCaseWithDBs):

    def setUp(self):
        self.login_url = '/auth/login/'
        self.regular_user = create_regular_user()

    @mock.patch("admin_cohort.auth.auth_backends.jwt_auth_service.check_credentials")
    def test_request_is_logged_after_login(self, mock_check_credentials: MagicMock):
        mock_check_credentials.return_value = True
        response = self.client.post(path=self.login_url,
                                    content_type="application/json",
                                    data={"username": self.regular_user.username,
                                          "password": "some-password"},
                                    headers={settings.AUTHORIZATION_METHOD_HEADER: settings.JWT_AUTH_MODE})
        mock_check_credentials.assert_called()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        request_log = APIRequestLog.objects.latest("id")
        self.assertEqual(request_log.path, self.login_url)
        self.assertEqual(request_log.method, "POST")
        self.assertEqual(request_log.status_code, status.HTTP_200_OK)
