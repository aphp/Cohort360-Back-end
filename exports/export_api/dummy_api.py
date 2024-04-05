import enum
import logging
from typing import Dict

from admin_cohort.settings import EXPORT_API_CONF
from admin_cohort.types import JobStatus


_logger = logging.getLogger('django.request')


class DummyAPI:

    class Services(enum.Enum):
        EXPORTS = "exports"

    def __init__(self):
        self.url = EXPORT_API_CONF.get('API_URL')
        api_version = EXPORT_API_CONF.get('API_VERSION')
        self.export_base_url = f"{self.url}{api_version}"
        self.target_environment = EXPORT_API_CONF.get('EXPORT_ENVIRONMENT')
        self.tokens = self.get_tokens()

    @staticmethod
    def get_tokens():
        api_tokens = EXPORT_API_CONF.get('TOKENS').split(',')
        token_by_service: Dict[DummyAPI.Services, str] = {}
        for token_item in api_tokens:
            service_name, token = token_item.split(':')
            try:
                token_by_service[DummyAPI.Services(service_name)] = token
            except ValueError as e:
                _logger.error(f"Unrecognized API service. Must be one of {[s.value for s in DummyAPI.Services]}")
                raise e
        return token_by_service

    def launch_export(self, params: dict) -> str:
        """
        @return: task_id: string, an export job id
        """
        raise NotImplementedError

    def get_job_status(self, job_id: str, service: Services) -> JobStatus:
        """
        @param job_id
        @param service, a service name on which the job is run
        @return: job_status: JobStatus
        """
        raise NotImplementedError

    def create_db(self, name: str, location: str) -> str:
        """
        @return: task_id: string, a DB creation job id
        """
        raise NotImplementedError

    def change_db_ownership(self, location: str, db_user: str) -> None:
        """
        @param location: DB path
        @param db_user:
        """
        raise NotImplementedError


class ApiJobStatus(enum.Enum):
    Received = 'Received'
    Running = 'Running'
    Pending = 'Pending'
    Revoked = 'Revoked'
    Failure = 'Failure'
    Finished = 'Finished'


status_mapper = {ApiJobStatus.Received.value: JobStatus.new,
                 ApiJobStatus.Pending.value: JobStatus.pending,
                 ApiJobStatus.Running.value: JobStatus.started,
                 ApiJobStatus.Failure.value: JobStatus.failed,
                 ApiJobStatus.Revoked.value: JobStatus.cancelled,
                 ApiJobStatus.Finished.value: JobStatus.finished
                 }
