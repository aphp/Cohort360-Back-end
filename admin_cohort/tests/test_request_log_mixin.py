from unittest import mock
from unittest.mock import MagicMock

from django.conf import settings
from django.test.client import Client
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_tracking.models import APIRequestLog

from admin_cohort.tests.tests_auth import create_regular_user
from admin_cohort.types import OIDCAuthTokens


class RequestLogMixinTests(APITestCase):

    def setUp(self):
        self.client = Client()
        self.login_url = '/auth/login/'
        self.regular_user = create_regular_user()

    @mock.patch("admin_cohort.auth.auth_backends.oidc_auth_service.retrieve_username")
    @mock.patch("admin_cohort.auth.auth_backends.oidc_auth_service.get_tokens")
    def test_request_is_logged_after_login(self, mock_get_tokens: MagicMock, mock_retrieve_username: MagicMock):
        mock_get_tokens.return_value = OIDCAuthTokens(access_token="aaa", refresh_token="rrr")
        mock_retrieve_username.return_value = self.regular_user.username
        response = self.client.post(path=self.login_url,
                                    content_type="application/json",
                                    data={"auth_code": "any-auth-code-will-do",
                                          "redirect_uri": "some-redirect-url"},
                                    headers={settings.AUTHORIZATION_METHOD_HEADER: settings.OIDC_AUTH_MODE})
        mock_get_tokens.assert_called()
        mock_retrieve_username.assert_called()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        request_log = APIRequestLog.objects.latest("id")
        self.assertEqual(request_log.path, self.login_url)
        self.assertEqual(request_log.method, "POST")
        self.assertEqual(request_log.status_code, status.HTTP_200_OK)
