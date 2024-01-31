import json
from unittest import mock
from unittest.mock import MagicMock

from requests import Response
from rest_framework import status
from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework_simplejwt.exceptions import InvalidToken

from accesses.models import Access, Perimeter, Role
from admin_cohort.models import User
from admin_cohort.settings import JWT_AUTH_MODE, OIDC_AUTH_MODE
from admin_cohort.tests.tests_tools import new_user_and_profile
from admin_cohort.types import JwtTokens, LoginError, ServerError, UserInfo
from admin_cohort.views import UserViewSet, token_refresh_view


def create_regular_user() -> User:
    return User.objects.create(firstname="Regular",
                               lastname="USER",
                               email="regular.user@aphp.fr",
                               username="12345")


class JWTLoginTests(APITestCase):

    def setUp(self):
        self.login_url = '/accounts/login/'
        self.regular_user = create_regular_user()
        self.unregistered_user_credentials = {"username": "spy-user",
                                              "password": "top-secret-007"}

    def test_login_method_not_allowed(self):
        response = self.client.patch(path=self.login_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @mock.patch("admin_cohort.auth.auth_backends.get_jwt_tokens")
    def test_login_with_unregistered_user(self, mock_get_jwt_tokens: MagicMock):
        mock_get_jwt_tokens.side_effect = User.DoesNotExist()
        response = self.client.post(path=self.login_url, data=self.unregistered_user_credentials)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch("admin_cohort.auth.auth_backends.get_jwt_tokens")
    def test_login_with_wrong_credentials(self, mock_get_jwt_tokens: MagicMock):
        mock_get_jwt_tokens.side_effect = LoginError("Invalid username or password")
        response = self.client.post(path=self.login_url, data={"username": self.regular_user.username,
                                                               "password": "wrong-psswd"})
        mock_get_jwt_tokens.assert_called()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch("admin_cohort.auth.auth_backends.get_jwt_tokens")
    def test_login_unavailable_jwt_server(self, mock_get_jwt_tokens: MagicMock):
        mock_get_jwt_tokens.side_effect = ServerError("JWT server unavailable")
        response = self.client.post(path=self.login_url, data={"username": self.regular_user.username,
                                                               "password": "psswd"})
        mock_get_jwt_tokens.assert_called()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch("admin_cohort.auth.auth_backends.get_jwt_tokens")
    def test_login_success(self, mock_get_jwt_tokens: MagicMock):
        mock_get_jwt_tokens.return_value = JwtTokens(access="aaa", refresh="rrr")
        response = self.client.post(path=self.login_url, data={"username": self.regular_user.username,
                                                               "password": "any-will-do"})
        mock_get_jwt_tokens.assert_called()
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class OIDCLoginTests(APITestCase):

    def setUp(self):
        self.login_url = '/auth/oidc/login/'
        self.regular_user = create_regular_user()

    def test_login_without_auth_code(self):
        response = self.client.post(path=self.login_url, data={"wrong_param": "doesnotmatter"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch("admin_cohort.auth.auth_backends.get_oidc_user_info")
    @mock.patch("admin_cohort.auth.auth_backends.get_oidc_tokens")
    def test_login_success(self, mock_get_oidc_tokens: MagicMock, mock_get_oidc_user_info: MagicMock):
        mock_get_oidc_tokens.return_value = JwtTokens(access_token="aaa", refresh_token="rrr")
        oidc_user_info_resp = Response()
        oidc_user_info_resp.status_code = status.HTTP_200_OK
        content = {"preferred_username": self.regular_user.username,
                   "given_name": self.regular_user.firstname,
                   "family_name": self.regular_user.lastname,
                   "email": self.regular_user.email
                   }
        oidc_user_info_resp._content = json.dumps(content, indent=2).encode('utf-8')
        mock_get_oidc_user_info.return_value = oidc_user_info_resp
        response = self.client.post(path=self.login_url, data={"auth_code": "any-auth-code-will-do"})
        mock_get_oidc_tokens.assert_called()
        mock_get_oidc_user_info.assert_called()
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AuthClassTests(APITestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.headers = {"HTTP_AUTHORIZATION": "Bearer SoMERaNdoMStRIng"}
        self.protected_url = '/users/'
        self.protected_view = UserViewSet
        self.regular_user, self.regular_profile = new_user_and_profile(firstname="Regular",
                                                                       lastname="USER",
                                                                       email="regular.user@aphp.fr")
        self.perimeter_aphp = Perimeter.objects.create(name="APHP", local_id="1")
        self.users_reader_role = Role.objects.create(name="USERS READER", right_read_users=True)
        self.users_reader_access = Access.objects.create(profile=self.regular_profile,
                                                         perimeter=self.perimeter_aphp,
                                                         role=self.users_reader_role)

    @mock.patch("admin_cohort.auth.auth_class.get_userinfo_from_token")
    def test_authenticate_success(self, mock_get_userinfo: MagicMock):
        mock_get_userinfo.return_value = UserInfo(username=self.regular_user.username,
                                                  firstname=self.regular_user.firstname,
                                                  lastname=self.regular_user.lastname,
                                                  email=self.regular_user.email)
        request = self.factory.get(path=self.protected_url, **self.headers)
        request.user = self.regular_user
        response = self.protected_view.as_view({'get': 'list'})(request)
        mock_get_userinfo.assert_called()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authenticate_without_token(self):
        request = self.factory.get(path=self.protected_url)
        response = self.protected_view.as_view({'get': 'list'})(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch("admin_cohort.auth.auth_class.get_userinfo_from_token")
    def test_authenticate_error(self, mock_get_userinfo: MagicMock):
        mock_get_userinfo.side_effect = InvalidToken()
        request = self.factory.get(path=self.protected_url, **self.headers)
        request.user = self.regular_user
        response = self.protected_view.as_view({'get': 'list'})(request)
        mock_get_userinfo.assert_called()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch("admin_cohort.auth.auth_class.get_userinfo_from_token")
    @mock.patch("admin_cohort.auth.auth_class.get_auth_data")
    def test_authenticate_error_with_bytes_token(self, mock_get_auth_data: MagicMock, mock_get_userinfo: MagicMock):
        mock_get_auth_data.return_value = (b"SoMERaNdoMbYteS", None)
        mock_get_userinfo.side_effect = InvalidToken()
        request = self.factory.get(path=self.protected_url)
        request.user = self.regular_user
        response = self.protected_view.as_view({'get': 'list'})(request)
        mock_get_auth_data.assert_called()
        mock_get_userinfo.assert_called()
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

    def test_refresh_token_with_invalid_auth_mode(self):
        request = self.factory.post(path=self.refresh_url)
        request.META["HTTP_AUTHORIZATIONMETHOD"] = "INVALID_AUTH_MODE"
        request.jwt_refresh_key = "SoMERaNdoMStRIngAsrEfREshTOkEn"
        response = token_refresh_view(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch("admin_cohort.views.auth.refresh_jwt_token")
    def test_refresh_token_with_jwt_auth_mode(self, mock_refresh_jwt_token: MagicMock):
        jwt_resp = Response()
        jwt_resp.status_code = status.HTTP_200_OK
        jwt_resp._content = b'{"access": "aaa", "refresh": "rrr"}'
        mock_refresh_jwt_token.return_value = jwt_resp
        request = self.factory.post(path=self.refresh_url)
        request.META["HTTP_AUTHORIZATIONMETHOD"] = JWT_AUTH_MODE
        request.jwt_refresh_key = "SoMERaNdoMStRIngAsrEfREshTOkEn"
        response = token_refresh_view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @mock.patch("admin_cohort.views.auth.refresh_oidc_token")
    def test_refresh_token_with_oidc_auth_mode(self, mock_refresh_oidc_token: MagicMock):
        oidc_resp = Response()
        oidc_resp.status_code = status.HTTP_200_OK
        oidc_resp._content = b'{"access_token": "aaa", "refresh_token": "rrr"}'
        mock_refresh_oidc_token.return_value = oidc_resp
        request = self.factory.post(path=self.refresh_url)
        request.META["HTTP_AUTHORIZATIONMETHOD"] = OIDC_AUTH_MODE
        request.jwt_refresh_key = "SoMERaNdoMStRIngAsrEfREshTOkEn"
        response = token_refresh_view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @mock.patch("admin_cohort.views.auth.refresh_jwt_token")
    def test_refresh_token_with_invalid_token(self, mock_refresh_jwt_token: MagicMock):
        jwt_resp = Response()
        jwt_resp.status_code = status.HTTP_401_UNAUTHORIZED
        mock_refresh_jwt_token.return_value = jwt_resp
        request = self.factory.post(path=self.refresh_url)
        request.META["HTTP_AUTHORIZATIONMETHOD"] = JWT_AUTH_MODE
        request.jwt_refresh_key = "SoMERaNdoMStRIngAsrEfREshTOkEn"
        response = token_refresh_view(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LogoutTests(APITestCase):

    def setUp(self):
        self.logout_url = '/accounts/logout/'

    def test_logout_method_not_allowed(self):
        response = self.client.patch(path=self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @mock.patch("admin_cohort.views.auth.logout_user")
    def test_logout_success(self, mock_logout_user: MagicMock):
        mock_logout_user.return_value = None
        response = self.client.post(path=self.logout_url)
        mock_logout_user.assert_called()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

