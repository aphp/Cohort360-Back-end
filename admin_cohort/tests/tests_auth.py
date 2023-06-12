import json
from unittest import mock
from unittest.mock import MagicMock

from requests import Response
from rest_framework import status
from rest_framework.test import APITestCase, APIRequestFactory

from admin_cohort.models import User
from admin_cohort.types import JwtTokens, LoginError, ServerError, UserInfo, TokenVerificationError
from admin_cohort.views import UserViewSet, token_refresh_view


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


class OIDCLoginTests(APITestCase):

    def setUp(self):
        self.login_url = '/auth/oidc/login/'
        self.regular_user = create_regular_user()

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


class AuthClassTests(APITestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.protected_url = '/users/'
        self.regular_user = create_regular_user()

    @mock.patch("admin_cohort.auth.auth_class.verify_token")
    def test_verify_token_success(self, mock_verify_token: MagicMock):
        random_token = "SoMERaNdoMStRIng"
        mock_verify_token.return_value = UserInfo(username=self.regular_user.provider_username,
                                                  firstname=self.regular_user.firstname,
                                                  lastname=self.regular_user.lastname,
                                                  email=self.regular_user.email)
        request = self.factory.get(path=self.protected_url)
        request.jwt_access_key = random_token
        response = UserViewSet.as_view({'get': 'list'})(request)
        mock_verify_token.assert_called()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @mock.patch("admin_cohort.auth.auth_class.verify_token")
    def test_verify_token_error(self, mock_verify_token: MagicMock):
        mock_verify_token.side_effect = TokenVerificationError()
        request = self.factory.get(path=self.protected_url)
        request.jwt_access_key = "SoMERaNdoMStRIng"
        response = UserViewSet.as_view({'get': 'list'})(request)
        mock_verify_token.assert_called()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch("admin_cohort.auth.auth_class.verify_token")
    @mock.patch("admin_cohort.auth.auth_class.get_token_from_headers")
    def test_verify_token_error_with_bytes_token(self, mock_get_token_from_headers: MagicMock, mock_verify_token: MagicMock):
        mock_get_token_from_headers.return_value = (b"SoMERaNdoMbYteS", None)
        mock_verify_token.side_effect = TokenVerificationError()
        request = self.factory.get(path=self.protected_url)
        response = UserViewSet.as_view({'get': 'list'})(request)
        mock_get_token_from_headers.assert_called()
        mock_verify_token.assert_called()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RefreshTokenTests(APITestCase):

    def setUp(self):
        self.refresh_url = '/accounts/refresh/'
        self.factory = APIRequestFactory()

    def test_refresh_token_method_not_allowed(self):
        request = self.factory.get(path=self.refresh_url)
        request.jwt_refresh_key = "SoMERaNdoMStRIngAsrEfREshTOkEn"
        response = token_refresh_view(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @mock.patch("admin_cohort.views.auth.refresh_oidc_token")
    @mock.patch("admin_cohort.views.auth.refresh_jwt_token")
    def test_refresh_token_jwt_InvalidToken_oidc_ok(self, mock_refresh_jwt_token: MagicMock, mock_refresh_oidc_token: MagicMock):
        # the jwt refresher will raise an Invalid Token error, the oidc will return refreshed tokens
        jwt_resp = Response()
        jwt_resp.status_code = status.HTTP_401_UNAUTHORIZED
        mock_refresh_jwt_token.__name__ = mock_refresh_jwt_token._mock_name
        mock_refresh_jwt_token.return_value = jwt_resp
        oidc_resp = Response()
        oidc_resp.status_code = status.HTTP_200_OK
        oidc_resp._content = b'{"access_token": "aaa", "refresh_token": "rrr"}'
        mock_refresh_oidc_token.return_value = oidc_resp
        request = self.factory.post(path=self.refresh_url)
        request.jwt_refresh_key = "SoMERaNdoMStRIngAsrEfREshTOkEn"
        response = token_refresh_view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @mock.patch("admin_cohort.views.auth.refresh_oidc_token")
    @mock.patch("admin_cohort.views.auth.refresh_jwt_token")
    def test_refresh_token_jwt_InvalidToken_oidc_RequestError(self, mock_refresh_jwt_token: MagicMock, mock_refresh_oidc_token: MagicMock):
        # the jwt refresher will raise an InvalidToken error, the oidc will raise RequestError
        jwt_resp = Response()
        jwt_resp.status_code = status.HTTP_401_UNAUTHORIZED
        oidc_resp = Response()
        oidc_resp.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        mock_refresh_jwt_token.__name__ = mock_refresh_jwt_token._mock_name
        mock_refresh_oidc_token.__name__ = mock_refresh_oidc_token._mock_name
        mock_refresh_jwt_token.return_value = jwt_resp
        mock_refresh_oidc_token.return_value = oidc_resp
        request = self.factory.post(path=self.refresh_url)
        request.jwt_refresh_key = "SoMERaNdoMStRIngAsrEfREshTOkEn"
        response = token_refresh_view(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = json.loads(response.content)
        self.assertEqual(len(response.get("errors")), 2)
