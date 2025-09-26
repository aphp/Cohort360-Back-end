from unittest import mock
from unittest.mock import MagicMock

from django.test.testcases import TestCase
from jwt import InvalidTokenError

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
from admin_cohort.services.auth import AuthService
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


class TestAuthenticateRequest(AuthBaseTests):

    def setUp(self):
        super().setUp()
        self.auth_service = AuthService()
        self.token = "test_token"
        self.auth_method = settings.JWT_AUTH_MODE
        self.headers = {}

    @mock.patch("admin_cohort.services.auth.AuthService._get_authenticator")
    def test_authenticate_request_success(self, mock_get_authenticator):
        mock_authenticator = MagicMock()
        mock_authenticator.authenticate.return_value = self.regular_user.username
        mock_get_authenticator.return_value = mock_authenticator

        self.auth_service.post_auth_hooks = []

        user, token = self.auth_service.authenticate_request(self.token, self.auth_method, self.headers)

        self.assertEqual(user, self.regular_user)
        self.assertEqual(token, self.token)
        mock_get_authenticator.assert_called_once_with(self.auth_method)
        mock_authenticator.authenticate.assert_called_once_with(token=self.token)
        for hook in self.auth_service.post_auth_hooks:
            hook.assert_called_once_with(self.regular_user, self.headers)

    @mock.patch("admin_cohort.services.auth.AuthService._get_authenticator")
    def test_authenticate_request_invalid_token(self, mock_get_authenticator):
        mock_authenticator = MagicMock()
        mock_authenticator.authenticate.side_effect = InvalidTokenError("Invalid token")
        mock_get_authenticator.return_value = mock_authenticator

        result = self.auth_service.authenticate_request(self.token, self.auth_method, self.headers)

        self.assertIsNone(result)

    @mock.patch("admin_cohort.services.auth.AuthService._get_authenticator")
    @mock.patch("admin_cohort.services.auth.User.objects.get")
    def test_authenticate_request_user_not_found(self, mock_user_get, mock_get_authenticator):
        mock_authenticator = MagicMock()
        mock_authenticator.authenticate.return_value = self.regular_user.username
        mock_get_authenticator.return_value = mock_authenticator
        mock_user_get.side_effect = User.DoesNotExist

        result = self.auth_service.authenticate_request(self.token, self.auth_method, self.headers)

        self.assertIsNone(result)

    def test_authenticate_request_no_token(self):
        result = self.auth_service.authenticate_request(None, self.auth_method, self.headers)
        self.assertIsNone(result)

    def test_authenticate_request_invalid_auth_method(self):
        with self.assertRaises(KeyError):
            self.auth_service.authenticate_request(self.token, "invalid_method", self.headers)


class AuthServiceTests(TestCase):

    @mock.patch('admin_cohort.services.auth.import_string')
    @mock.patch('admin_cohort.services.auth.apps')
    @mock.patch('admin_cohort.services.auth.settings')
    def test_load_post_auth_hooks_no_hooks(self, mock_settings, mock_apps, mock_import_string):
        """
        Test that load_post_auth_hooks returns an empty list when no hooks are defined.
        """
        mock_settings.INCLUDED_APPS = ['app1', 'app2']

        mock_app_config = MagicMock()
        mock_app_config.POST_AUTH_HOOKS = []
        mock_apps.get_app_config.return_value = mock_app_config

        hooks = AuthService.load_post_auth_hooks()

        self.assertEqual(hooks, [])
        mock_import_string.assert_not_called()

    @mock.patch('admin_cohort.services.auth.import_string')
    @mock.patch('admin_cohort.services.auth.apps')
    @mock.patch('admin_cohort.services.auth.settings')
    def test_load_post_auth_hooks_valid_hooks(self, mock_settings, mock_apps, mock_import_string):
        """
        Test that load_post_auth_hooks correctly loads valid hooks.
        """
        mock_settings.INCLUDED_APPS = ['app1']

        mock_hook_func = MagicMock()
        mock_import_string.return_value = mock_hook_func

        mock_app_config = MagicMock()
        mock_app_config.POST_AUTH_HOOKS = ['my.hook.path']
        mock_apps.get_app_config.return_value = mock_app_config

        hooks = AuthService.load_post_auth_hooks()

        self.assertEqual(hooks, [mock_hook_func])
        mock_import_string.assert_called_once_with('my.hook.path')
        mock_apps.get_app_config.assert_called_once_with('app1')

    @mock.patch('admin_cohort.services.auth.import_string')
    @mock.patch('admin_cohort.services.auth.apps')
    @mock.patch('admin_cohort.services.auth.settings')
    def test_load_post_auth_hooks_invalid_hook(self, mock_settings, mock_apps, mock_import_string):
        """
        Test that load_post_auth_hooks handles ImportErrors gracefully.
        """
        mock_settings.INCLUDED_APPS = ['app1']

        mock_import_string.side_effect = ImportError

        mock_app_config = MagicMock()
        mock_app_config.POST_AUTH_HOOKS = ['invalid.hook.path']
        mock_apps.get_app_config.return_value = mock_app_config

        with self.assertLogs('admin_cohort.services.auth', level='ERROR') as cm:
            hooks = AuthService.load_post_auth_hooks()
            self.assertIn("Improperly configured post authentication hook `invalid.hook.path`", cm.output[0])

        self.assertEqual(hooks, [])
        mock_import_string.assert_called_once_with('invalid.hook.path')

    @mock.patch('admin_cohort.services.auth.import_string')
    @mock.patch('admin_cohort.services.auth.apps')
    @mock.patch('admin_cohort.services.auth.settings')
    def test_load_post_auth_hooks_mixed_valid_and_invalid(self, mock_settings, mock_apps, mock_import_string):
        """
        Test that load_post_auth_hooks loads valid hooks even if some are invalid.
        """
        mock_settings.INCLUDED_APPS = ['app1']

        mock_hook_func = MagicMock()
        mock_import_string.side_effect = [mock_hook_func, ImportError]

        mock_app_config = MagicMock()
        mock_app_config.POST_AUTH_HOOKS = ['valid.hook.path', 'invalid.hook.path']
        mock_apps.get_app_config.return_value = mock_app_config

        with self.assertLogs('admin_cohort.services.auth', level='ERROR'):
            hooks = AuthService.load_post_auth_hooks()

        self.assertEqual(hooks, [mock_hook_func])
        self.assertEqual(mock_import_string.call_count, 2)

    @mock.patch('admin_cohort.services.auth.import_string')
    @mock.patch('admin_cohort.services.auth.apps')
    @mock.patch('admin_cohort.services.auth.settings')
    def test_load_post_auth_hooks_app_without_hooks_attribute(self, mock_settings, mock_apps, mock_import_string):
        """
        Test that load_post_auth_hooks handles apps without POST_AUTH_HOOKS attribute.
        """
        mock_settings.INCLUDED_APPS = ['app1']

        class AppConfigWithoutHooks:
            pass

        mock_app_config = AppConfigWithoutHooks()
        mock_apps.get_app_config.return_value = mock_app_config

        hooks = AuthService.load_post_auth_hooks()

        self.assertEqual(hooks, [])
        mock_import_string.assert_not_called()

    @mock.patch.object(AuthService, 'authenticate_request')
    def test_authenticate_ws_request_success(self, mock_authenticate_request):
        """
        Test that authenticate_ws_request returns a user on successful authentication.
        """
        service = AuthService()
        mock_user = MagicMock(spec=User)
        mock_authenticate_request.return_value = (mock_user, 'some_token')

        user = service.authenticate_ws_request(token='some_token', auth_method='some_method', headers={})

        self.assertEqual(user, mock_user)
        mock_authenticate_request.assert_called_once_with(token='some_token', auth_method='some_method', headers={})

    @mock.patch.object(AuthService, 'authenticate_request')
    def test_authenticate_ws_request_failure(self, mock_authenticate_request):
        """
        Test that authenticate_ws_request returns None on failed authentication.
        """
        service = AuthService()
        mock_authenticate_request.return_value = None

        with self.assertLogs('admin_cohort.services.auth', level='INFO') as cm:
            user = service.authenticate_ws_request(token='some_token', auth_method='some_method', headers={})
            self.assertIn("Error authenticating WS request", cm.output[0])

        self.assertIsNone(user)
        mock_authenticate_request.assert_called_once_with(token='some_token', auth_method='some_method', headers={})
