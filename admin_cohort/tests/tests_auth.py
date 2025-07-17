from unittest import mock
from unittest.mock import MagicMock


from rest_framework import status
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from rest_framework_simplejwt.exceptions import InvalidToken
from django.test import Client
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware

from accesses.models import Perimeter
from admin_cohort.models import User
from admin_cohort.tests.tests_tools import new_user_and_profile, TestCaseWithDBs
from admin_cohort.types import OIDCAuthTokens, JWTAuthTokens
from admin_cohort.exceptions import ServerError
from admin_cohort.views import UserViewSet, LogoutView, TokenRefreshView, LoginView


def create_regular_user() -> User:
    return User.objects.create(firstname="Regular",
                               lastname="USER",
                               email="regular.user@aphp.fr",
                               username="12345")


class AuthBaseTests(APITestCase, TestCaseWithDBs):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = Client()
        self.regular_user = create_regular_user()

    def _add_session_to_request(self, request):
        middleware = SessionMiddleware(get_response=lambda r: r)
        middleware.process_request(request)
        request.session.save()


class JWTLoginTests(AuthBaseTests):

    def setUp(self):
        super().setUp()
        self.headers = {settings.AUTHORIZATION_METHOD_HEADER: settings.JWT_AUTH_MODE}
        self.login_url = '/auth/login/'

        self.unregistered_user_credentials = {"username": "spy-user",
                                              "password": "top-secret-007"}

    def test_login_method_not_allowed(self):
        request = self.factory.patch(path=self.login_url)
        self._add_session_to_request(request)
        response = LoginView.as_view({'patch': 'post'})(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @mock.patch("admin_cohort.auth.auth_backends.jwt_auth_service.check_credentials")
    def test_login_with_unregistered_user(self, mock_check_credentials: MagicMock):
        mock_check_credentials.return_value = True
        request = self.factory.post(path=self.login_url,
                                    data=self.unregistered_user_credentials,
                                    headers=self.headers)
        self._add_session_to_request(request)
        response = LoginView.as_view({'post': 'post'})(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch("admin_cohort.auth.auth_backends.jwt_auth_service.check_credentials")
    def test_login_with_wrong_credentials(self, mock_check_credentials: MagicMock):
        mock_check_credentials.return_value = False
        request = self.factory.post(path=self.login_url,
                                    data={"username": self.regular_user.username,
                                          "password": "wrong-psswd"},
                                    headers=self.headers)
        self._add_session_to_request(request)
        response = LoginView.as_view({'post': 'post'})(request)
        mock_check_credentials.assert_called()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch("admin_cohort.auth.auth_backends.jwt_auth_service.check_credentials")
    def test_login_unavailable_id_checker_server(self, mock_check_credentials: MagicMock):
        mock_check_credentials.side_effect = ServerError("ID checker server unavailable")
        request = self.factory.post(path=self.login_url,
                                    data={"username": self.regular_user.username,
                                          "password": "psswd"},
                                    headers=self.headers)
        self._add_session_to_request(request)
        response = LoginView.as_view({'post': 'post'})(request)
        mock_check_credentials.assert_called()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch("admin_cohort.auth.auth_backends.jwt_auth_service.check_credentials")
    def test_login_success(self, mock_check_credentials: MagicMock):
        mock_check_credentials.return_value = True
        request = self.factory.post(path=self.login_url,
                                    data={"username": self.regular_user.username,
                                          "password": "any-will-do"},
                                    headers=self.headers)
        self._add_session_to_request(request)
        response = LoginView.as_view({'post': 'post'})(request)
        mock_check_credentials.assert_called()
        self.assertEqual(response.status_code, status.HTTP_200_OK)


if settings.ENABLE_OIDC_AUTH:
    class OIDCLoginTests(AuthBaseTests):

        def setUp(self):
            super().setUp()
            self.headers = {settings.AUTHORIZATION_METHOD_HEADER: settings.OIDC_AUTH_MODE}
            self.login_url = '/auth/login/'


        def test_login_without_auth_code(self):
            response = self.client.post(path=self.login_url,
                                        content_type="application/json",
                                        data={"not_auth_code": "value"},
                                        headers=self.headers)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        @mock.patch("admin_cohort.auth.auth_backends.oidc_auth_service.retrieve_username")
        @mock.patch("admin_cohort.auth.auth_backends.oidc_auth_service.get_tokens")
        def test_login_success(self, mock_get_tokens: MagicMock, mock_retrieve_username: MagicMock):
            mock_get_tokens.return_value = OIDCAuthTokens(access_token="aaa", refresh_token="rrr")
            mock_retrieve_username.return_value = self.regular_user.username
            response = self.client.post(path=self.login_url,
                                        content_type="application/json",
                                        data={"auth_code": "any-auth-code-will-do",
                                              "redirect_uri": "some-redirect-url"},
                                        headers=self.headers)
            mock_get_tokens.assert_called()
            mock_retrieve_username.assert_called()
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class AuthClassTests(AuthBaseTests):

    def setUp(self):
        super().setUp()
        self.headers = {"HTTP_AUTHORIZATION": "Bearer SoMERaNdoMStRIng"}
        self.protected_url = '/users/'
        self.protected_view = UserViewSet
        self.regular_user, self.regular_profile = new_user_and_profile()
        self.perimeter_aphp = Perimeter.objects.create(name="APHP", local_id="1")

    @mock.patch("admin_cohort.auth.auth_class.auth_service.authenticate_http_request")
    def test_authenticate_success(self, mock_authenticate_http_request: MagicMock):
        mock_authenticate_http_request.return_value = self.regular_user, "some_token"
        request = self.factory.get(path=self.protected_url, **self.headers)
        request.user = self.regular_user
        response = self.protected_view.as_view({'get': 'list'})(request)
        mock_authenticate_http_request.assert_called()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authenticate_without_token(self):
        request = self.factory.get(path=self.protected_url)
        response = self.protected_view.as_view({'get': 'list'})(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch("admin_cohort.auth.auth_class.auth_service.authenticate_http_request")
    def test_authenticate_error(self, mock_authenticate_http_request: MagicMock):
        mock_authenticate_http_request.return_value = None
        request = self.factory.get(path=self.protected_url, **self.headers)
        request.user = self.regular_user
        response = self.protected_view.as_view({'get': 'list'})(request)
        mock_authenticate_http_request.assert_called()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RefreshTokenTests(AuthBaseTests):

    def setUp(self):
        super().setUp()
        self.refresh_url = '/auth/refresh/'

    def test_refresh_token_method_not_allowed(self):
        request = self.factory.get(path=self.refresh_url,
                                   content_type="application/json",
                                   data={"refresh_token": "any-auth-code-will-do"},
                                   headers={"Authorization": "Bearer any-auth",
                                            settings.AUTHORIZATION_METHOD_HEADER: settings.OIDC_AUTH_MODE})
        force_authenticate(request, self.regular_user)
        response = TokenRefreshView.as_view({'get': 'post'})(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_refresh_token_with_invalid_auth_mode(self):
        with self.assertRaises(KeyError):
            request = self.factory.post(path=self.refresh_url,
                                        content_type="application/json",
                                        data={"refresh_token": "any-auth-code-will-do"},
                                        headers={"Authorization": "Bearer any-auth",
                                                 settings.AUTHORIZATION_METHOD_HEADER: "INVALID_AUTH_MODE"})
            self._add_session_to_request(request)
            force_authenticate(request, self.regular_user)
            _ = TokenRefreshView.as_view({'post': 'post'})(request)

    @mock.patch("admin_cohort.views.auth.auth_service.refresh_token")
    def test_refresh_token_with_jwt_auth_mode(self, mock_refresh_token: MagicMock):
        mock_refresh_token.return_value = JWTAuthTokens(access="aaa", refresh="rrr")
        request = self.factory.post(path=self.refresh_url,
                                    content_type="application/json",
                                    data={"refresh_token": "any-jwt-token"},
                                    headers={"Authorization": "Bearer any-auth",
                                             settings.AUTHORIZATION_METHOD_HEADER: settings.JWT_AUTH_MODE})
        self._add_session_to_request(request)
        force_authenticate(request, self.regular_user)
        response = TokenRefreshView.as_view({'post': 'post'})(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @mock.patch("admin_cohort.views.auth.auth_service.refresh_token")
    def test_refresh_token_with_oidc_auth_mode(self, mock_refresh_token: MagicMock):
        mock_refresh_token.return_value = OIDCAuthTokens(access_token="aaa", refresh_token="rrr")
        request = self.factory.post(path=self.refresh_url,
                                    content_type="application/json",
                                    data={"refresh_token": "any-oidc-token"},
                                    headers={"Authorization": "Bearer any-auth",
                                             settings.AUTHORIZATION_METHOD_HEADER: settings.OIDC_AUTH_MODE})
        self._add_session_to_request(request)
        force_authenticate(request, self.regular_user)
        response = TokenRefreshView.as_view({'post': 'post'})(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @mock.patch("admin_cohort.views.auth.auth_service.refresh_token")
    def test_refresh_token_with_invalid_token(self, mock_refresh_token: MagicMock):
        mock_refresh_token.side_effect = InvalidToken("invalid token")
        request = self.factory.post(path=self.refresh_url,
                                    content_type="application/json",
                                    data={"refresh_token": "any-auth-code-will-do"},
                                    headers={"Authorization": "Bearer any-auth",
                                             settings.AUTHORIZATION_METHOD_HEADER: settings.JWT_AUTH_MODE})
        self._add_session_to_request(request)
        force_authenticate(request, self.regular_user)
        response = TokenRefreshView.as_view({'post': 'post'})(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LogoutTests(AuthBaseTests):

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.logout_url = '/auth/logout/'

    def test_logout_method_not_allowed(self):
        request = self.factory.patch(self.logout_url)
        force_authenticate(request, self.regular_user)
        response = LogoutView.as_view({'patch': 'post'})(request)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @mock.patch("admin_cohort.views.auth.auth_service.logout")
    def test_success_logout_from_jwt_session(self, mock_logout: MagicMock):
        request = self.factory.post(path=self.logout_url,
                                    headers={"AuthorizationMethod": settings.JWT_AUTH_MODE})
        self._add_session_to_request(request)
        force_authenticate(request, self.regular_user)
        mock_logout.return_value = None
        response = LogoutView.as_view({'post': 'post'})(request)
        mock_logout.assert_called()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @mock.patch("admin_cohort.views.auth.auth_service.logout")
    def test_success_logout_from_oidc_session(self, mock_logout: MagicMock):
        request = self.factory.post(path=self.logout_url,
                                    data={"refresh_token": "any-token-will-do"},
                                    headers={settings.AUTHORIZATION_METHOD_HEADER: settings.OIDC_AUTH_MODE})
        self._add_session_to_request(request)
        force_authenticate(request, self.regular_user)
        mock_logout.return_value = None
        response = LogoutView.as_view({'post': 'post'})(request)
        mock_logout.assert_called()
        self.assertEqual(response.status_code, status.HTTP_200_OK)

