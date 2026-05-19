import unittest
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from admin_cohort.middleware.context_request_middleware import (
    ContextRequestHolder,
    ContextRequestMiddleware,
    context_request,
    get_request_user_id,
    get_trace_id,
)


class GetTraceIdTests(unittest.TestCase):
    def tearDown(self):
        context_request.set(None)

    def test_returns_uuid_when_no_request_in_context(self):
        context_request.set(None)
        trace_id = get_trace_id()
        self.assertIsInstance(trace_id, str)
        self.assertEqual(len(trace_id), 36)  # uuid4 string

    def test_returns_header_value_when_present(self):
        request = MagicMock()
        request.headers = {settings.TRACE_ID_HEADER: "header-trace"}
        request.META = {}
        context_request.set(request)
        self.assertEqual(get_trace_id(), "header-trace")

    def test_falls_back_to_meta_when_header_absent(self):
        request = MagicMock()
        request.headers = {}
        request.META = {f"HTTP_{settings.TRACE_ID_HEADER}": "meta-trace"}
        context_request.set(request)
        self.assertEqual(get_trace_id(), "meta-trace")


class GetRequestUserIdTests(unittest.TestCase):
    @patch("admin_cohort.services.auth.auth_service.authenticate_http_request")
    def test_returns_anonymous_when_auth_fails(self, mock_auth):
        mock_auth.return_value = None
        self.assertEqual(get_request_user_id(MagicMock()), "Anonymous")

    @patch("admin_cohort.services.auth.auth_service.authenticate_http_request")
    def test_returns_username_when_authenticated(self, mock_auth):
        user = MagicMock(username="alice")
        mock_auth.return_value = (user, "token")
        self.assertEqual(get_request_user_id(MagicMock()), "alice")


class ContextRequestHolderTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_sets_and_resets_context(self):
        request = self.factory.get("/x")
        request.META[f"HTTP_{settings.TRACE_ID_HEADER}"] = "existing"
        self.assertIsNone(context_request.get())
        with ContextRequestHolder(request):
            self.assertIs(context_request.get(), request)
        self.assertIsNone(context_request.get())

    def test_injects_trace_id_header_when_missing(self):
        request = self.factory.get("/x")
        request.headers = {}
        with ContextRequestHolder(request):
            self.assertIn(f"HTTP_{settings.TRACE_ID_HEADER}", request.META)


@patch("admin_cohort.middleware.context_request_middleware.logger")
class ContextRequestMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.response = MagicMock(status_code=200, headers={})
        self.get_response = MagicMock(return_value=self.response)
        self.middleware = ContextRequestMiddleware(self.get_response)

    @patch("admin_cohort.middleware.context_request_middleware.get_request_user_id", return_value="bob")
    def test_call_populates_environ_and_adds_process_time_header(self, _, __):
        request = self.factory.get("/x", **{f"HTTP_{settings.TRACE_ID_HEADER}": "t-1"})
        result = self.middleware(request)
        self.assertEqual(request.environ["user_id"], "bob")
        self.assertEqual(request.environ["trace_id"], "t-1")
        self.assertEqual(request.environ["impersonating"], "-")
        self.assertIn("X-Process-Time", result.headers)
        self.get_response.assert_called_once_with(request)

    @patch("admin_cohort.middleware.context_request_middleware.get_request_user_id", return_value="Anonymous")
    def test_call_generates_trace_id_when_header_missing(self, _, __):
        request = self.factory.get("/x")
        self.middleware(request)
        self.assertEqual(len(request.environ["trace_id"]), 36)

    @patch("admin_cohort.middleware.context_request_middleware.get_request_user_id", return_value="bob")
    def test_call_picks_up_impersonating_header(self, _, __):
        request = self.factory.get("/x", **{f"HTTP_{settings.IMPERSONATING_HEADER}": "carol"})
        self.middleware(request)
        self.assertEqual(request.environ["impersonating"], "carol")
