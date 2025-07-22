import logging
from typing import Literal

import requests

from exporters.apps import ExportersConfig

_logger = logging.getLogger('django.request')


class BaseAPI:
    conf_key: Literal["HADOOP_API", "EXPORT_API"]

    def __init__(self):
        self.api_conf = ExportersConfig.THIRD_PARTY_API_CONF.get(self.conf_key)
        self.url = self.api_conf.get('API_URL')
        self.auth_token = self.api_conf.get('AUTH_TOKEN')
        self.task_status_endpoint = self.api_conf.get('TASK_STATUS_ENDPOINT')

    def get_export_logs(self, job_id: str) -> dict:
        params = {"task_uuid": job_id,
                  "return_out_logs": True,
                  "return_err_logs": True
                  }
        response = requests.get(url=f"{self.url}{self.task_status_endpoint}",
                                params=params,
                                headers={'auth-token': self.auth_token})
        return response.json()
