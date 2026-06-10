import os
import tempfile
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status


class MetricsViewTests(TestCase):
    databases = {"default"}

    def setUp(self):
        self.url = reverse("metrics")

    def test_single_process_exposes_metrics(self):
        with patch.dict(os.environ, clear=False):
            os.environ.pop("PROMETHEUS_MULTIPROC_DIR", None)
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/plain", response["Content-Type"])
        self.assertIn(b"cohort360_jobs_in_progress", response.content)

    def test_multiproc_dir_invalid_falls_back(self):
        with patch.dict(os.environ, {"PROMETHEUS_MULTIPROC_DIR": "/nonexistent/path"}):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"cohort360_jobs_in_progress", response.content)

    @patch("admin_cohort.views.metrics.multiprocess.MultiProcessCollector")
    def test_multiproc_dir_valid_registers_collector(self, mock_collector):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"PROMETHEUS_MULTIPROC_DIR": tmp}):
                response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_collector.assert_called_once()
        self.assertIn(b"cohort360_jobs_in_progress", response.content)
