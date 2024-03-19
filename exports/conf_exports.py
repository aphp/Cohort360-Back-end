import enum
import logging
import os
import time
from datetime import datetime

import requests
from django.utils import timezone
from hdfs import HdfsError
from hdfs.ext.kerberos import KerberosClient
from requests import Response, HTTPError, RequestException
from rest_framework import status

from admin_cohort.tools import prettify_dict
from admin_cohort.types import JobStatus, MissingDataError
from exports.emails import push_email_notification, export_request_failed
from exports.models import ExportRequest, Export
from exports.types import HdfsServerUnreachableError, ExportType

_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')
env = os.environ

INFRA_EXPORT_TOKEN = env.get('INFRA_EXPORT_TOKEN')
INFRA_HADOOP_TOKEN = env.get('INFRA_HADOOP_TOKEN')
INFRA_API_URL = env.get('INFRA_API_URL')
EXPORT_HIVE_URL = f"{INFRA_API_URL}/bigdata/data_exporter/hive/"
EXPORT_CSV_URL = f"{INFRA_API_URL}/bigdata/data_exporter/csv/"
HADOOP_NEW_DB_URL = f"{INFRA_API_URL}/hadoop/hive/create_base_hive"
HADOOP_CHOWN_DB_URL = f"{INFRA_API_URL}/hadoop/hdfs/chown_directory"
HIVE_DB_FOLDER = env.get('HIVE_DB_FOLDER')
HIVE_EXPORTER_USER = env.get('HIVE_EXPORTER_USER')
OMOP_ENVIRONMENT = env.get('EXPORT_OMOP_ENVIRONMENT')


class ApiJobStatus(enum.Enum):
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


class JobStatusResponse:
    def __init__(self, job_status: str, out: str = None, err: str = None):
        self.job_status = status_mapper.get(job_status, JobStatus.unknown)
        self.out = out
        self.err = err

    @property
    def has_ended(self):
        return self.job_status in [JobStatus.failed, JobStatus.cancelled,
                                   JobStatus.finished, JobStatus.unknown]


class PostJobResponse:
    def __init__(self, response: Response, url: str):
        if not status.is_success(response.status_code):
            raise HTTPError(f"Connection error ({url}) : status code {response.text}")
        res = response.json()
        if 'task_id' not in res:
            raise MissingDataError(f"Response from Infra API is missing 'task_id'. Received: {prettify_dict(res)}")
        self.task_id: str = res.get('task_id')


class HadoopApiResponse:
    def __init__(self, **kwargs):
        self.status = kwargs.get('status')
        self.ret_code = kwargs.get('ret_code')
        self.out = kwargs.get('out')
        self.err = kwargs.get('err')

    @property
    def has_failed(self) -> bool:
        return self.status != "success" or self.ret_code != 0

    @property
    def detail_err(self) -> str:
        return f"status was {self.status} and ret_code {self.ret_code}.\n"\
               f"err returned is : {self.err}"


status_mapper = {ApiJobStatus.Pending.value: JobStatus.pending,
                 ApiJobStatus.Retry.value: JobStatus.pending,
                 ApiJobStatus.Running.value: JobStatus.started,
                 ApiJobStatus.FinishedSuccessfully.value: JobStatus.finished,
                 ApiJobStatus.FinishedWithError.value: JobStatus.failed,
                 ApiJobStatus.FinishedWithTimeout.value: JobStatus.failed,
                 ApiJobStatus.flowerNotAccessible.value: JobStatus.failed,
                 ApiJobStatus.Failure.value: JobStatus.failed,
                 ApiJobStatus.NotFound.value: JobStatus.failed,
                 ApiJobStatus.Revoked.value: JobStatus.cancelled
                 }


def log_export_request_task(id, msg):
    _logger.info(f"[ExportTask] [ExportRequest: {id}] {msg}")


def mark_export_request_as_failed(er: ExportRequest, e: Exception, msg: str, start: datetime):
    err_msg = f"{msg}: {e}"
    _logger_err.error(f"[ExportTask] [ExportRequest: {er.pk}] {err_msg}")
    er.request_job_fail_msg = err_msg
    if er.request_job_status in [JobStatus.pending, JobStatus.validated, JobStatus.new]:
        er.request_job_status = JobStatus.failed
    er.request_job_duration = timezone.now() - start
    try:
        notification_data = dict(recipient_name=er.owner.display_name,
                                 recipient_email=er.owner.email,
                                 cohort_id=er.cohort_id,
                                 cohort_name=er.cohort_name,
                                 error_message=er.request_job_fail_msg)
        push_email_notification(base_notification=export_request_failed, **notification_data)
    except OSError:
        _logger_err.error(f"[ExportTask] [ExportRequest: {er.pk}] Error sending export failure email notification")
    else:
        er.is_user_notified = True
    er.save()

# API REQUESTS ###############################################################


def post_hadoop(url: str, data: dict):
    resp = requests.post(url=url, params=data, headers={'auth-token': INFRA_HADOOP_TOKEN})
    resp.raise_for_status()
    if status.is_success(resp.status_code):
        res = HadoopApiResponse(**resp.json())
        if res.has_failed:
            raise HTTPError(f"{resp.status_code} - {res.detail_err}")


def get_job_status(service: str, job_id: str) -> JobStatusResponse:
    params = {"task_uuid": job_id,
              "return_out_logs": True,
              "return_err_logs": True
              }
    job_status_url = f"{INFRA_API_URL}/{service}/task_status"
    auth_token = service == "hadoop" and INFRA_HADOOP_TOKEN or INFRA_EXPORT_TOKEN
    response = requests.get(url=job_status_url, params=params, headers={'auth-token': auth_token})
    if not status.is_success(response.status_code):
        raise HTTPError(f"Error getting job status from Infra API: {response.text}")
    response = response.json()
    return JobStatusResponse(job_status=response.get('task_status'),
                             out=response.get('stdout'),
                             err=response.get('stderr'))

# PROCESSES ###############################################################


def change_hive_db_ownership(export_request: ExportRequest, db_user: str):
    log_export_request_task(export_request.id, f"Granting rights on DB '{export_request.target_name}' to user '{db_user}'")
    data = {"location": export_request.target_full_path,
            "uid": db_user,
            "gid": "hdfs",
            "recursive": True}
    try:
        post_hadoop(url=HADOOP_CHOWN_DB_URL, data=data)
        log_export_request_task(export_request.id, f"DB '{export_request.target_name}' attributed to {HIVE_EXPORTER_USER} and HDFS.")
    except RequestException as e:
        raise RequestException(f"Error granting rights on DB '{export_request.target_name}'") from e


def wait_for_hive_db_creation_job(job_id):
    errors_count = 0
    status_resp = JobStatusResponse(job_status=ApiJobStatus.Pending.value)

    while errors_count < 5 and not status_resp.has_ended:
        time.sleep(5)
        try:
            status_resp = get_job_status(service="hadoop", job_id=job_id)
        except RequestException:
            errors_count += 1

    if status_resp.job_status != JobStatus.finished:
        raise HTTPError(f"Error on creating Hive DB {status_resp.err or 'No `err` value returned'}")
    elif errors_count >= 5:
        raise HTTPError("5 consecutive errors during Hive DB creation")


def create_hive_db(export_request: ExportRequest):
    log_export_request_task(export_request.id, f"Creating DB '{export_request.target_name}', location: {export_request.target_full_path}")
    data = {"name": export_request.target_name,
            "location": export_request.target_full_path,
            "if_not_exists": False}
    try:
        response = requests.post(url=HADOOP_NEW_DB_URL, params=data, headers={'auth-token': INFRA_HADOOP_TOKEN})
        response = PostJobResponse(response=response, url=HADOOP_NEW_DB_URL)
        log_export_request_task(export_request.id, f"Received Hive DB creation task_id: {response.task_id}")
        wait_for_hive_db_creation_job(response.task_id)
        log_export_request_task(export_request.id, f"DB '{export_request.target_name}' created.")
    except RequestException as e:
        _logger_err.error(f"Error on call to create Hive DB: {e}")
        raise e


def prepare_hive_db(export_request: ExportRequest):
    create_hive_db(export_request=export_request)
    change_hive_db_ownership(export_request=export_request, db_user=HIVE_EXPORTER_USER)


def post_export(export_request: ExportRequest) -> str:
    log_export_request_task(export_request.id, f"Asking to export for '{export_request.target_name}'")
    tables = ",".join([t.omop_table_name for t in export_request.tables.all()])
    params = {"cohort_id": export_request.cohort_fk.fhir_group_id,
              "tables": tables,
              "environment": OMOP_ENVIRONMENT,
              "no_date_shift": export_request.nominative or not export_request.shift_dates,
              "overwrite": False,
              "user_for_pseudo": not export_request.nominative and export_request.target_unix_account.name or None,
              }
    if export_request.output_format == ExportType.HIVE:
        url = EXPORT_HIVE_URL
        params.update({"database_name": export_request.target_name})
    else:
        url = EXPORT_CSV_URL
        params.update({"file_path": export_request.target_full_path})
    resp = requests.post(url=url, params=params, headers={'auth-token': INFRA_EXPORT_TOKEN})
    return PostJobResponse(response=resp, url=url).task_id


def post_export_v1(export: Export) -> str:
    log_export_request_task(export.uuid, f"Asking to export for '{export.target_name}'")
    tables = ",".join([f"{table.name}:{table.cohort_result_subset.fhir_group_id}:{table.respect_table_relationships}"
                       for table in export.export_tables.all()])
    params = {"tables": tables,
              "environment": OMOP_ENVIRONMENT,
              "no_date_shift": not export.nominative and export.shift_dates,
              "overwrite": False,
              "user_for_pseudo": not export.nominative and export.datalab.name or None,
              }
    if export.output_format == ExportType.HIVE:
        url = EXPORT_HIVE_URL
        params.update({"database_name": export.target_name})
    else:
        url = EXPORT_CSV_URL
        params.update({"file_path": export.target_full_path})
    resp = requests.post(url=url, params=params, headers={'auth-token': INFRA_EXPORT_TOKEN})
    return PostJobResponse(response=resp, url=url).task_id


def wait_for_export_job(er: ExportRequest):
    errors_count = 0
    error_msg = ""
    status_resp = JobStatusResponse(job_status=ApiJobStatus.Pending.value)

    while errors_count < 5 and not status_resp.has_ended:
        time.sleep(5)
        log_export_request_task(er.pk, f"Asking for status of job {er.request_job_id}.")
        try:
            status_resp = get_job_status(service="bigdata", job_id=er.request_job_id)
            log_export_request_task(er.pk, f"Status received: {status_resp.job_status} - Err: {status_resp.err or ''}")
            if er.request_job_status != status_resp.job_status:
                er.request_job_status = status_resp.job_status
                er.save()
        except RequestException as e:
            log_export_request_task(er.pk, f"Status not received: {e}")
            errors_count += 1
            error_msg = str(e)

    if status_resp.job_status != JobStatus.finished:
        raise HTTPError(status_resp.err or "No 'err' value returned.")
    elif errors_count >= 5:
        raise HTTPError(f"5 times internal error during task -> {error_msg}")


def conclude_export_hive(export_request: ExportRequest):
    db_user = export_request.target_unix_account.name
    change_hive_db_ownership(export_request=export_request, db_user=db_user)
    log_export_request_task(export_request.id, f"DB '{export_request.target_name}' attributed to {db_user}. Conclusion finished.")


# FILES EXTRACT ###############################################################

HDFS_SERVERS = env.get("HDFS_SERVERS").split(',')


HDFS_CLIENTS_DICT = {'current': HDFS_SERVERS[0],
                     HDFS_SERVERS[0]: KerberosClient(HDFS_SERVERS[0])}


def try_other_hdfs_servers():
    for server in [s for s in HDFS_SERVERS if s != HDFS_CLIENTS_DICT['current']]:
        cl = KerberosClient(server)
        try:
            cl.status('/')
        except HdfsError:
            continue
        else:
            HDFS_CLIENTS_DICT[server] = KerberosClient(server)
            HDFS_CLIENTS_DICT['current'] = server
            return cl
    raise HdfsServerUnreachableError("HDFS servers are unreachable or in stand-by")


def get_client():
    cl = HDFS_CLIENTS_DICT.get(HDFS_CLIENTS_DICT['current'])
    try:
        cl.status('/')
    except HdfsError:
        return try_other_hdfs_servers()
    else:
        return cl


def stream_gen(file_name: str):
    with get_client().read(hdfs_path=file_name, offset=0, length=None, encoding=None, chunk_size=1000000,
                           delimiter=None, progress=None) as f:
        for chunk in f:
            yield chunk


def get_file_size(file_name: str) -> int:
    return get_client().status(hdfs_path=file_name).get("length")


def delete_file(file_name: str):
    get_client().delete(hdfs_path=file_name)
