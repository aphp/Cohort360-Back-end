import logging
from typing import Literal

import requests

from admin_cohort.types import JobStatus
from exporters.apps import ExportersConfig
from exporters.enums import status_mapper

_logger = logging.getLogger('django.request')


class BaseAPI:
    conf_key: Literal["INFRA_API", "EXPORT_API"]

    def __init__(self):
        self.api_conf = ExportersConfig.THIRD_PARTY_API_CONF.get(self.conf_key)
        self.url = self.api_conf.get('API_URL')
        self.task_status_endpoint = self.api_conf.get('TASK_STATUS_ENDPOINT')
        self.auth_token = self.api_conf.get('AUTH_TOKEN')

    def get_job_status(self, job_id: str) -> JobStatus:
        params = {"task_uuid": job_id,
                  "return_out_logs": True,
                  "return_err_logs": True
                  }
        response = requests.get(url=f"{self.url}{self.task_status_endpoint}",
                                params=params,
                                headers={'auth-token': self.auth_token})
        response = response.json()
        return status_mapper.get(response.get('task_status'),
                                 JobStatus.unknown)