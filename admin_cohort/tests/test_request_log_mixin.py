from unittest import mock
from unittest.mock import MagicMock

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_tracking.models import APIRequestLog

from admin_cohort.tests.tests_auth import create_regular_user
from admin_cohort.types import AuthTokens


class RequestLogMixinTests(APITestCase):

    def setUp(self):
        super().setUp()
        self.login_url = '/auth/login/'
        self.regular_user = create_regular_user()

    @mock.patch("admin_cohort.auth.auth_backends.auth_service.get_tokens")
    def test_request_is_logged_after_login(self, mock_get_tokens: MagicMock):
        mock_get_tokens.return_value = AuthTokens(access_token="aaa", refresh_token="rrr")
        response = self.client.post(path=self.login_url, data={"username": self.regular_user.username,
                                                               "password": "any-will-do"})
        mock_get_tokens.assert_called()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        request_log = APIRequestLog.objects.latest("id")
        self.assertEqual(request_log.path, '/auth/login/')
        self.assertEqual(request_log.user_id, self.regular_user.username)
        self.assertEqual(request_log.method, "POST")
        self.assertEqual(request_log.status_code, status.HTTP_200_OK)
