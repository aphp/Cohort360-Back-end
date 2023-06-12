from unittest import mock
from unittest.mock import MagicMock

from rest_framework import status
from rest_framework.test import APITestCase

from admin_cohort.models import User
from admin_cohort.types import JwtTokens, LoginError, ServerError, UserInfo


def create_regular_user() -> User:
    return User.objects.create(firstname="Regular",
                               lastname="USER",
                               email="regular.user@aphp.fr",
                               provider_username="12345")


class JWTLoginTests(APITestCase):

    def setUp(self):
        self.login_url = '/accounts/login/'
        self.regular_user = create_regular_user()
        self.unregistered_user_credentials = {"username": "spy-user",
                                              "password": "top-secret-007"}

    @mock.patch("admin_cohort.auth.auth_backends.get_jwt_tokens")
    def test_login_with_unregistered_user(self, mock_get_jwt_tokens: MagicMock):
        mock_get_jwt_tokens.side_effect = User.DoesNotExist()
        response = self.client.post(path=self.login_url, data=self.unregistered_user_credentials)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch("admin_cohort.auth.auth_backends.get_jwt_tokens")
    def test_login_with_wrong_credentials(self, mock_get_jwt_tokens: MagicMock):
        mock_get_jwt_tokens.side_effect = LoginError("Invalid username or password")
        response = self.client.post(path=self.login_url, data={"username": self.regular_user.provider_username,
                                                               "password": "wrong-psswd"})
        mock_get_jwt_tokens.assert_called()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch("admin_cohort.auth.auth_backends.get_jwt_tokens")
    def test_login_unavailable_jwt_server(self, mock_get_jwt_tokens: MagicMock):
        mock_get_jwt_tokens.side_effect = ServerError("JWT server unavailable")
        response = self.client.post(path=self.login_url, data={"username": self.regular_user.provider_username,
                                                               "password": "psswd"})
        mock_get_jwt_tokens.assert_called()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch("admin_cohort.auth.auth_backends.get_jwt_tokens")
    def test_login_success(self, mock_get_jwt_tokens: MagicMock):
        mock_get_jwt_tokens.return_value = JwtTokens(access="aaa", refresh="rrr")
        response = self.client.post(path=self.login_url, data={"username": self.regular_user.provider_username,
                                                               "password": "any-will-do"})
        mock_get_jwt_tokens.assert_called()
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class OIDCLoginTests(JWTLoginTests):

    def setUp(self):
        super(OIDCLoginTests, self).setUp()
        self.login_url = '/auth/oidc/login/'

    @mock.patch("admin_cohort.auth.auth_backends.get_oidc_user_info")
    @mock.patch("admin_cohort.auth.auth_backends.get_oidc_tokens")
    def test_login_success(self, mock_get_oidc_tokens: MagicMock, mock_get_oidc_user_info: MagicMock):
        mock_get_oidc_tokens.return_value = JwtTokens(access_token="aaa", refresh_token="rrr")
        mock_get_oidc_user_info.return_value = UserInfo(preferred_username=self.regular_user.provider_username,
                                                        given_name=self.regular_user.firstname,
                                                        family_name=self.regular_user.lastname,
                                                        email=self.regular_user.email)
        response = self.client.post(path=self.login_url, data={"auth_code": "any-auth-code-will-do"})
        mock_get_oidc_tokens.assert_called()
        mock_get_oidc_user_info.assert_called()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
