from unittest.mock import MagicMock

from django.conf import settings
from rest_framework.test import APIRequestFactory

from admin_cohort.middleware.jwt_session_middleware import JWTSessionMiddleware
from admin_cohort.tests.tests_tools import TestCaseWithDBs


class JWTSessionMiddlewareTests(TestCaseWithDBs):

    def setUp(self):
        self.get_response = MagicMock()
        self.middleware = JWTSessionMiddleware(self.get_response)
        self.factory = APIRequestFactory()
        self.test_safe_route = "/accesses/roles/"
        self.test_logout_route = "/auth/logout/"
        self.cookies = {settings.SESSION_COOKIE_NAME: "SOMESESSIONCOOKIE",
                        settings.CSRF_COOKIE_NAME: "SOMECSRFCOOKIE"
                        }

    def test_set_cookies_in_process_request(self):
        request = self.factory.get(path=self.test_safe_route)
        request.COOKIES = self.cookies
        self.middleware.process_request(request)
        self.assertEqual(request.META.get('HTTP_SESSION_ID'), self.cookies.get(settings.SESSION_COOKIE_NAME))

    def test_delete_cookies_after_logout(self):
        request = self.factory.get(path=self.test_logout_route)
        request.COOKIES = self.cookies
        response: MagicMock = self.middleware(request)
        self.assertEqual(response.delete_cookie.call_count, 1)
