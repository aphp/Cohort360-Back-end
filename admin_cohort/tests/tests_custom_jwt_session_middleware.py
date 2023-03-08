from unittest import TestCase
from unittest.mock import MagicMock

from rest_framework.test import APIRequestFactory

from admin_cohort.AuthMiddleware import CustomJwtSessionMiddleware
from admin_cohort.settings import JWT_SESSION_COOKIE, JWT_REFRESH_COOKIE


class CustomJwtSessionMiddlewareTests(TestCase):

    def setUp(self):
        self.get_response = MagicMock()
        self.middleware = CustomJwtSessionMiddleware(self.get_response)
        self.factory = APIRequestFactory()
        self.test_safe_route = "/accesses/roles/"
        self.test_logout_route = "/accounts/logout/"
        self.cookies = {JWT_SESSION_COOKIE: "SOMESESSIONACCESSCOOKIE",
                        JWT_REFRESH_COOKIE: "SOMESESSIONREFERESHCOOKIE"
                        }

    def test_set_cookies_in_process_request(self):
        request = self.factory.get(path=self.test_safe_route)
        request.COOKIES = self.cookies
        self.middleware.process_request(request)
        self.assertEqual(getattr(request, "jwt_session_key", False), self.cookies.get(JWT_SESSION_COOKIE))
        self.assertEqual(getattr(request, "jwt_refresh_key", False), self.cookies.get(JWT_REFRESH_COOKIE))

    def test_delete_cookies_after_logout(self):
        request = self.factory.get(path=self.test_logout_route)
        request.COOKIES = self.cookies
        response: MagicMock = self.middleware(request)
        self.assertEqual(response.delete_cookie.call_count, 2)
        self.assertEqual(response.delete_cookie.call_args_list[0].args, (JWT_SESSION_COOKIE,))
        self.assertEqual(response.delete_cookie.call_args_list[1].args, (JWT_REFRESH_COOKIE,))

    def test_set_cookies_on_response(self):
        request = self.factory.get(path=self.test_safe_route)
        request.COOKIES = self.cookies
        self.middleware.process_request(request)
        self.get_response.content = "{}"
        response: MagicMock = self.middleware.process_response(request, self.get_response)
        self.assertEqual(response.set_cookie.call_count, 2)
        self.assertEqual(response.set_cookie.call_args_list[0].args, (JWT_SESSION_COOKIE, self.cookies.get(JWT_SESSION_COOKIE)))
        self.assertEqual(response.set_cookie.call_args_list[1].args, (JWT_REFRESH_COOKIE, self.cookies.get(JWT_REFRESH_COOKIE)))
