from django.test import TestCase, RequestFactory
from unittest.mock import MagicMock, patch

from django.views.debug import SafeExceptionReporterFilter

from admin_cohort.tools.except_report_filter import CustomExceptionReporterFilter


class CustomExceptionReporterFilterTests(TestCase):

    def setUp(self):
        self.filter = CustomExceptionReporterFilter()
        self.request_factory = RequestFactory()

    def test_get_safe_settings(self):
        """Test that get_safe_settings hides settings."""
        safe_settings = self.filter.get_safe_settings()
        self.assertEqual(list(safe_settings.keys()), ["hidden"])

    def test_get_safe_request_meta(self):
        """Test that get_safe_request_meta hides request META."""
        request = self.request_factory.get("/")
        safe_meta = self.filter.get_safe_request_meta(request)
        self.assertEqual(list(safe_meta.keys()), ["hidden"])

    def test_get_post_parameters_hides_sensitive_data(self):
        """Test that get_post_parameters redacts sensitive fields."""
        request = self.request_factory.post("/", {"password": "secret", "other": "visible"})
        request.POST = request.POST.copy()

        post_params = self.filter.get_post_parameters(request)
        self.assertEqual(post_params["password"], self.filter.cleansed_substitute)
        self.assertEqual(post_params["other"], "visible")

    @patch.object(SafeExceptionReporterFilter, 'get_traceback_frame_variables')
    def test_get_traceback_frame_variables_hides_sensitive_data(self, mock_super_call):
        """Test that get_traceback_frame_variables redacts sensitive fields."""
        mock_super_call.return_value={"password": "not-cleansed", "other": "visible"}
        tb_frame = MagicMock()
        tb_frame.f_locals = {"password": "secret", "other": "visible"}

        filtered_variables = dict(self.filter.get_traceback_frame_variables(None, tb_frame))

        self.assertEqual(filtered_variables["password"], self.filter.cleansed_substitute)
        self.assertEqual(filtered_variables["other"], "visible")
