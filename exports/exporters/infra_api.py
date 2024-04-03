import enum
import os
from enum import Enum

from requests import Response, RequestException
from rest_framework import status

from admin_cohort.types import JobStatus


class InfraAPI:

    def __init__(self):
        env = os.environ
        self.api_url = env.get('INFRA_API_URL')
        api_exporter_version = env.get('DATA_EXPORTER_VERSION')
        self.export_base_url = f"{self.api_url}/bigdata/data_exporter{api_exporter_version}"
        self.target_environment = env.get('EXPORT_OMOP_ENVIRONMENT')
        self.bigdata_auth_token = env.get('INFRA_EXPORT_TOKEN')
        self.hadoop_auth_token = env.get('INFRA_HADOOP_TOKEN')
        self.required_table = "person"

    class Services(Enum):
        BIG_DATA = "bigdata"
        HADOOP = "hadoop"


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


class JobResponse:
    def __init__(self, response: Response):
        if not status.is_success(response.status_code):
            raise RequestException(f"Error connecting to `{response.url}`: {response.status_code} - {response.text}")
        self.task_id = response.json().get('task_id')


class JobStatusResponse:
    def __init__(self, response: Response = None) -> None:
        if response:
            if not status.is_success(response.status_code):
                raise RequestException(f"Error getting job status from Infra API: {response.text}")
            response = response.json()
            self.job_status = status_mapper.get(response.get('task_status'), JobStatus.unknown)
            self.out = response.get('stdout')
            self.err = response.get('stderr')
        else:
            self.job_status = JobStatus.pending

    @property
    def job_ended(self):
        return self.job_status in [JobStatus.failed, JobStatus.cancelled,
                                   JobStatus.finished, JobStatus.unknown]


class HiveDbOwnershipResponse:
    def __init__(self, response):
        if not status.is_success(response.status_code):
            raise RequestException(response.text)
        response = response.json()
        self.status = response.get('status')
        self.ret_code = response.get('ret_code')
        self.err = response.get('err')

    @property
    def has_failed(self) -> bool:
        return self.status != "success" or self.ret_code != 0


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
