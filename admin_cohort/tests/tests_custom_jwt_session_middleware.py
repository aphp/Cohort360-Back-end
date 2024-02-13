from unittest import TestCase
from unittest.mock import MagicMock

from django.conf.global_settings import CSRF_COOKIE_NAME
from rest_framework.test import APIRequestFactory

from admin_cohort.middleware.jwt_session_middleware import JWTSessionMiddleware
from admin_cohort.settings import SESSION_COOKIE_NAME, ACCESS_TOKEN_COOKIE


class JWTSessionMiddlewareTests(TestCase):

    def setUp(self):
        self.get_response = MagicMock()
        self.middleware = JWTSessionMiddleware(self.get_response)
        self.factory = APIRequestFactory()
        self.test_safe_route = "/accesses/roles/"
        self.test_logout_route = "/accounts/logout/"
        self.cookies = {SESSION_COOKIE_NAME: "SOMESESSIONCOOKIE",
                        ACCESS_TOKEN_COOKIE: "SOMESESSIONACCESSCOOKIE",
                        CSRF_COOKIE_NAME: "SOMECSRFCOOKIE"
                        }

    def test_set_cookies_in_process_request(self):
        request = self.factory.get(path=self.test_safe_route)
        request.COOKIES = self.cookies
        self.middleware.process_request(request)
        self.assertEqual(request.META.get('HTTP_SESSION_ID'), self.cookies.get(SESSION_COOKIE_NAME))

    def test_delete_cookies_after_logout(self):
        request = self.factory.get(path=self.test_logout_route)
        request.COOKIES = self.cookies
        response: MagicMock = self.middleware(request)
        self.assertEqual(response.delete_cookie.call_count, 2)
