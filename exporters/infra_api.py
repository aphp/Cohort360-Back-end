import enum
import logging
from typing import Dict

import requests
from django.conf import settings
from requests import Response, RequestException
from rest_framework import status

from admin_cohort.types import JobStatus


_logger = logging.getLogger('django.request')


class InfraAPI:

    class Services(enum.Enum):
        BIG_DATA = "bigdata"
        HADOOP = "hadoop"

    def __init__(self):
        api_conf = settings.EXPORT_API_CONF
        self.url = api_conf.get('API_URL')
        api_exporter_version = api_conf.get('API_VERSION')
        self.export_base_url = f"{self.url}/bigdata/data_exporter{api_exporter_version}"
        self.target_environment = api_conf.get('EXPORT_ENVIRONMENT')
        self.tokens = self.get_tokens(api_conf.get('TOKENS'))
        self.required_table = "person"  # todo: remove this when working with new export models

    @staticmethod
    def get_tokens(tokens: str):
        api_tokens = tokens.split(',')
        token_by_service: Dict[InfraAPI.Services, str] = {}
        for token_item in api_tokens:
            service_name, token = token_item.split(':')
            try:
                token_by_service[InfraAPI.Services(service_name)] = token
            except ValueError as e:
                _logger.error(f"Unrecognized API service. Must be one of {[s.value for s in InfraAPI.Services]}")
                raise e
        return token_by_service

    def launch_export(self, params: dict) -> str:
        export_type = params.pop('export_type')
        response = requests.post(url=f"{self.export_base_url}/{export_type.value}",
                                 params=params,
                                 headers={'auth-token': self.tokens[self.Services.BIG_DATA]})
        return response.json().get('task_id')

    def get_job_status(self, job_id: str, service: Services) -> JobStatus:
        params = {"task_uuid": job_id,
                  "return_out_logs": True,
                  "return_err_logs": True
                  }
        response = requests.get(url=f"{self.url}/{service.value}/task_status",
                                params=params,
                                headers={'auth-token': self.tokens[service]})
        response = response.json()
        return status_mapper.get(response.get('task_status'),
                                 JobStatus.unknown)

    def create_db(self, name: str, location: str) -> str:
        params = {"name": name,
                  "location": location,
                  "if_not_exists": False
                  }
        response = self.query_hadoop(endpoint="hive/create_base_hive", params=params)
        return response.json().get('task_id')

    def change_db_ownership(self, location: str, db_user: str) -> None:
        params = {"location": location,
                  "uid": db_user,
                  "gid": "hdfs",
                  "recursive": True
                  }
        response = self.query_hadoop(endpoint="hdfs/chown_directory", params=params)
        self.check_response(response=response)

    def query_hadoop(self, endpoint: str, params: dict) -> Response:
        return requests.post(url=f"{self.url}/hadoop/{endpoint}",
                             params=params,
                             headers={'auth-token': self.tokens[self.Services.HADOOP]})

    @staticmethod
    def check_response(response):
        if not status.is_success(response.status_code):
            raise RequestException(response.text)
        response = response.json()
        if response.get('status') != "success" or response.get('ret_code') != 0:
            raise RequestException(f"Granting rights did not succeed: {response.get('err')}")


class InfraApiJobStatus(enum.Enum):
    Received = 'Received'
    Running = 'Running'
    Pending = 'Pending'
    NotFound = 'NotFound'
    Revoked = 'Revoked'
    Retry = 'Retry'
    Failure = 'Failure'
    FinishedSuccessfully = 'FinishedSuccessfully'
    FinishedWithError = 'FinishedWithError'
    FinishedWithTimeout = 'FinishedWithTimeout'
    flowerNotAccessible = 'flowerNotAccessible'


status_mapper = {InfraApiJobStatus.Received.value: JobStatus.new,
                 InfraApiJobStatus.Pending.value: JobStatus.pending,
                 InfraApiJobStatus.Retry.value: JobStatus.pending,
                 InfraApiJobStatus.Running.value: JobStatus.started,
                 InfraApiJobStatus.FinishedSuccessfully.value: JobStatus.finished,
                 InfraApiJobStatus.FinishedWithError.value: JobStatus.failed,
                 InfraApiJobStatus.FinishedWithTimeout.value: JobStatus.failed,
                 InfraApiJobStatus.flowerNotAccessible.value: JobStatus.failed,
                 InfraApiJobStatus.Failure.value: JobStatus.failed,
                 InfraApiJobStatus.NotFound.value: JobStatus.failed,
                 InfraApiJobStatus.Revoked.value: JobStatus.cancelled
                 }
