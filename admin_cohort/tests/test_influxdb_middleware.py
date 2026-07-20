from unittest.mock import patch

import certifi
from django.test import SimpleTestCase, override_settings

from admin_cohort.middleware.influxdb_middleware import InfluxDBMiddleware


class InfluxDBMiddlewareTests(SimpleTestCase):
    @override_settings(INFLUXDB_URL="https://influx.example", INFLUXDB_TOKEN="token")
    @patch("admin_cohort.middleware.influxdb_middleware.InfluxDBClient")
    def test_client_uses_certifi_ca_bundle(self, mock_client_cls):
        InfluxDBMiddleware(lambda request: None)

        mock_client_cls.assert_called_once_with(
            url="https://influx.example",
            token="token",
            ssl_ca_cert=certifi.where(),
        )
