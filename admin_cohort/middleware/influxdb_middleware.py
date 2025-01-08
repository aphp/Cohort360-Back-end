from time import time
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import ASYNCHRONOUS

from django.conf import settings


class InfluxDBMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.client = InfluxDBClient(url=settings.INFLUXDB_URL, token=settings.INFLUXDB_TOKEN)

    def __call__(self, request):
        if settings.INFLUXDB_ENABLED:
            return self.get_response(request)

        start_time = time()
        try:
            response = self.get_response(request)
        finally:
            end_time = time()
            tags = {'method': request.method,
                    'path': request.path_info,
                    'env': not settings.DEBUG and 'prod' or 'dev_qua',
                    }
            fields = {'response_time': (end_time - start_time) * 10 ** 3}
            point = {'measurement': 'django_requests',
                     'tags': tags,
                     'fields': fields,
                     'time': int(end_time * 10 ** 9)
                     }
            write_api = self.client.write_api(write_options=ASYNCHRONOUS)
            write_api.write(settings.INFLUXDB_BUCKET, settings.INFLUXDB_ORG, point)
        return response
