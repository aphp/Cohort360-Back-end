import enum
import logging

import requests
from requests import Response, RequestException
from rest_framework import status

from admin_cohort.types import JobStatus
from exporters.apps import ExportersConfig
from exporters.enums import ExportTypes

_logger = logging.getLogger('django.request')


class InfraAPI:

    class Services(enum.Enum):
        BIG_DATA = "bigdata"
        HADOOP = "hadoop"

    def __init__(self):
        api_conf = ExportersConfig.EXPORT_API_CONF
        self.url = api_conf.get('API_URL')
        self.export_endpoints = {
            ExportTypes.CSV: api_conf.get('CSV_EXPORT_ENDPOINT'),
            ExportTypes.XLSX: api_conf.get('XLSX_EXPORT_ENDPOINT'),
            ExportTypes.HIVE: api_conf.get('HIVE_EXPORT_ENDPOINT')
        }
        self.export_task_status_endpoint = api_conf.get('EXPORT_TASK_STATUS_ENDPOINT')
        self.hadoop_task_status_endpoint = api_conf.get('HADOOP_TASK_STATUS_ENDPOINT')
        self.create_db_endpoint = api_conf.get('CREATE_DB_ENDPOINT')
        self.alter_db_endpoint = api_conf.get('ALTER_DB_ENDPOINT')
        self.target_environment = api_conf.get('EXPORT_ENVIRONMENT')
        self.bigdata_token = api_conf.get('BIGDATA_TOKEN')
        self.hadoop_token = api_conf.get('HADOOP_TOKEN')
        self.required_table = "person"  # todo: remove this when working with new export models

    def launch_export(self, params: dict) -> str:
        export_type = params.pop('export_type')
        params["environment"] = self.target_environment
        endpoint = self.export_endpoints.get(ExportTypes(export_type))
        response = requests.post(url=f"{self.url}{endpoint}",
                                 params=params,
                                 headers={'auth-token': self.bigdata_token})
        return response.json().get('task_id')

    def get_job_status(self, job_id: str, service: Services) -> JobStatus:
        params = {"task_uuid": job_id,
                  "return_out_logs": True,
                  "return_err_logs": True
                  }
        endpoint, token = self.export_task_status_endpoint, self.bigdata_token
        if service == InfraAPI.Services.HADOOP:
            endpoint, token = self.hadoop_task_status_endpoint, self.hadoop_token

        response = requests.get(url=f"{self.url}{endpoint}",
                                params=params,
                                headers={'auth-token': token})
        response = response.json()
        return status_mapper.get(response.get('task_status'),
                                 JobStatus.unknown)

    def create_db(self, name: str, location: str) -> str:
        params = {"name": name,
                  "location": location,
                  "if_not_exists": False
                  }
        response = self.query_hadoop(endpoint=self.create_db_endpoint, params=params)
        return response.json().get('task_id')

    def change_db_ownership(self, location: str, db_user: str) -> None:
        params = {"location": location,
                  "uid": db_user,
                  "gid": "hdfs",
                  "recursive": True
                  }
        response = self.query_hadoop(endpoint=self.alter_db_endpoint, params=params)
        self.check_response(response=response)

    def query_hadoop(self, endpoint: str, params: dict) -> Response:
        return requests.post(url=f"{self.url}{endpoint}",
                             params=params,
                             headers={'auth-token': self.hadoop_token})

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
