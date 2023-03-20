from time import time
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import ASYNCHRONOUS

from admin_cohort.settings import INFLUXDB_DISABLED, INFLUXDB_BUCKET, INFLUXDB_ORG, INFLUXDB_URL, INFLUXDB_TOKEN, DEBUG


class InfluxDBMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN)

    def __call__(self, request):
        if INFLUXDB_DISABLED:
            return self.get_response(request)

        start_time = time()
        try:
            response = self.get_response(request)
        finally:
            end_time = time()
            tags = {'method': request.method,
                    'path': request.path_info,
                    'env': not DEBUG and 'prod' or 'dev_qua',
                    }
            fields = {'response_time': (end_time - start_time) * 10 ** 3}
            point = {'measurement': 'django_requests',
                     'tags': tags,
                     'fields': fields,
                     'time': int(end_time * 10 ** 9)
                     }
            write_api = self.client.write_api(write_options=ASYNCHRONOUS)
            write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)
        return response
