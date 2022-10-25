import enum
import json
from typing import Dict, List

import environ
import requests
import simplejson
from hdfs import HdfsError
from hdfs.ext.kerberos import KerberosClient
from requests import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

from admin_cohort.models import JobStatus
from admin_cohort.tools import prettify_dict
from .models import ExportRequest
from .types import ApiJobResponse, HdfsServerUnreachableError

env = environ.Env()

# EXPORTS JOBS ################################################################

INFRA_EXPORT_TOKEN = env('INFRA_EXPORT_TOKEN')
INFRA_HADOOP_TOKEN = env('INFRA_HADOOP_TOKEN')

INFRA_API_URL = f"{env('INFRA_API_URL')}"
EXPORT_HIVE_URL = f"{INFRA_API_URL}/bigdata/data_exporter/hive/"
CSV_URL = f"{INFRA_API_URL}/bigdata/data_exporter/csv/"
JOB_STATUS_URL = f"{INFRA_API_URL}/bigdata/task_status"
HADOOP_NEW_DB_URL = f"{INFRA_API_URL}/hadoop/hive/create_base_hive"
HADOOP_CHOWN_DB_URL = f"{INFRA_API_URL}/hadoop/hdfs/chown_directory"
HIVE_DB_LOCATION = "/apps/hive/warehouse/bigdata"
HIVE_DB_FOLDER = env('HIVE_DB_FOLDER')
HIVE_EXPORTER_USER = env('HIVE_EXPORTER_USER')
OMOP_ENVIRONMENT = env('EXPORT_OMOP_ENVIRONMENT')


class ApiJobStatutes(enum.Enum):
    #: Task state is unknown (assumed pending since you know the id).
    pending = 'PENDING'
    #: Task was received by a worker (only used in events).
    received = 'RECEIVED'
    #: Task was started by a worker (:setting:`task_track_started`).
    started = 'STARTED'
    #: Task succeeded
    success = 'SUCCESS'
    #: Task failed
    failure = 'FAILURE'
    #: Task was revoked.
    revoked = 'REVOKED'
    #: Task was rejected (only used in events).
    rejected = 'REJECTED'
    #: Task is waiting for retry.
    retry = 'RETRY'
    ignored = 'IGNORED'


dct_api_to_job_status = {
    ApiJobStatutes.pending.value: JobStatus.pending,
    ApiJobStatutes.received.value: JobStatus.pending,
    ApiJobStatutes.started.value: JobStatus.started,
    ApiJobStatutes.success.value: JobStatus.finished,
    ApiJobStatutes.failure.value: JobStatus.failed,
    ApiJobStatutes.revoked.value: JobStatus.cancelled,
    ApiJobStatutes.rejected.value: JobStatus.failed,
    ApiJobStatutes.retry.value: JobStatus.pending,
    ApiJobStatutes.ignored.value: JobStatus.failed,
}

# TOOLS ###############################################################


def log_export_request_task(id, msg):
    print(f"[ExportTask] [ExportRequest: {id}] {msg}")


def build_location(db_name: str) -> str:
    return f"{HIVE_DB_LOCATION}/{HIVE_DB_FOLDER}/{db_name}.db"

# API RESPONSES ###############################################################


class JobResult:
    def __init__(self, **kwargs):
        try:
            self.status: ApiJobStatutes = ApiJobStatutes[
                kwargs.get('status', None)]
        except ValueError:
            raise Exception(f"Status received from Infra API is not expected: "
                            f"{kwargs.get('status', None)}")
        self.ret_code: int = kwargs.get('ret_code', None)
        self.out: str = kwargs.get('out', None)
        self.err: str = kwargs.get('err', None)


class JobStatusResponse:
    def __init__(self, **kwargs):
        self.task_status: str = kwargs.get('task_status', None)
        if 'task_result' not in kwargs:
            raise Exception(f"Response from Infra API is missing 'task_result'."
                            f" What was received : {kwargs}")
        self.task_result: JobResult = JobResult(
            **kwargs.get('task_result')) \
            if kwargs.get('task_result') is not None else None


class PostJobResponse:
    def __init__(self, **kwargs):
        if 'task_id' not in kwargs:
            raise Exception(f"Response from Infra API not expected: "
                            f"missing 'task_id' - "
                            f"received : {prettify_dict(kwargs)}")
        self.task_id: str = kwargs.get('task_id', None)


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
        return f"status was {self.status} and ret_code {self.ret_code}.\n" \
               f"err returned is : {self.err}"


def check_resp(resp: Response, url: str) -> Dict:
    if not status.is_success(resp.status_code):
        raise Exception(f"Connection error ({url}) : status code {resp.text}")

    try:
        return resp.json()
    except (simplejson.JSONDecodeError, json.JSONDecodeError, ValueError):
        raise Exception(f"Response from Infra API ({url}) not readable: "
                        f"status code {resp.status_code} - "
                        f"{resp.text}")

# API REQUESTS ###############################################################


def post_hadoop(url: str, data: dict):
    """
    Given a particular Url, will follow Infra API/hadoop's convention
    and auth token to post data and process the response
    @param url: actual url to use
    @param data: data to post
    @return:
    """
    resp = requests.post(url, params=data,
                         headers={'auth-token': INFRA_HADOOP_TOKEN})

    status_code_msg = f"(http status {resp.status_code})"

    if status.is_success(resp.status_code):
        try:
            res = HadoopApiResponse(**resp.json())
        except Exception as e:
            raise Exception(f"{status_code_msg} response incomplete -> {e}")

        if res.has_failed:
            raise Exception(f"{status_code_msg} - {res.detail_err}")
    else:
        raise Exception(f"{status_code_msg} {resp.text}")


def post_export_hive(er: ExportRequest) -> str:
    """
    Asks Infra API to start a job of exporting data to a database built
    for the ExportRequest
    @param er:
    @return: the id of the asynchronous task generated
    """
    log_export_request_task(er.id, f"Asking for export to {er.target_name}")

    tables: List[str] = [t.omop_table_name for t in er.tables.all()]

    resp = requests.post(
        EXPORT_HIVE_URL,
        params=dict(
            user=er.target_unix_account.name,
            cohort_id=er.cohort_fk.fhir_group_id,
            tables=",".join(tables),
            is_pseudo=not er.nominative,
            database_name=er.target_name,
            environment=OMOP_ENVIRONMENT,
        ),
        headers={'auth-token': INFRA_EXPORT_TOKEN}
    )

    res = check_resp(resp, EXPORT_HIVE_URL)
    return PostJobResponse(**res).task_id


def post_export_csv(er: ExportRequest) -> str:
    """
    Asks Infra API to start a job of exporting csv data
    for the ExportRequest
    @param er:
    @return: the id of the asynchronous task generated
    """
    log_export_request_task(er.id, f"Asking for export to {er.target_name}")

    tables: List[str] = [t.omop_table_name for t in er.tables.all()]

    resp = requests.post(
        CSV_URL,
        params=dict(
            user="None",
            cohort_id=er.cohort_fk.fhir_group_id,
            tables=",".join(tables),
            compressed_file_path=er.target_full_path.replace(".zip", ""),
            is_pseudo=not er.nominative,
            environment=OMOP_ENVIRONMENT,
        ),
        headers={'auth-token': INFRA_EXPORT_TOKEN}
    )

    res = check_resp(resp, CSV_URL)
    return PostJobResponse(**res).task_id


def get_job_status(export_job_id: str) -> ApiJobResponse:
    """
    Returns the status of the job of the ExpRequest, and returns it
    using ApiJobResponse format, providing also output and/or error messages
    @param er: ExpRequest to get info about
    @return: ApiJobResponse: info about the job
    """
    resp = requests.get(
        url=JOB_STATUS_URL, params=dict(
            task_uuid=export_job_id,
            return_out_logs=False,
            return_err_logs=False,
        ),
        headers={'auth-token': INFRA_EXPORT_TOKEN}
    )

    res = check_resp(resp, JOB_STATUS_URL)

    jsr = JobStatusResponse(**res)

    j_status = dct_api_to_job_status.get(jsr.task_status, JobStatus.unknown)

    err = ""
    if j_status == JobStatus.unknown:
        err = f"Job status unknown : {jsr.task_status}."
        if jsr.task_result is not None:
            jsr.task_result.err = err

    if jsr.task_result is not None:
        err = f"{jsr.task_result.ret_code} - {jsr.task_result.err}"

    return ApiJobResponse(
        status=j_status,
        output=jsr.task_result.out if jsr.task_result is not None else "",
        err=err)

# PROCESSES ###############################################################


def prepare_hive_db(er: ExportRequest):
    """
    Ask Infra API to create a database that will receive exported data, and
    allocates Infra server's user an ownership to it to allow exporting
    @param er:
    @return:
    """
    location = build_location(er.target_name)
    log_export_request_task(er.id, f"Creating database with name "
                                   f"'{er.target_name}', location: {location}")

    try:
        post_hadoop(
            HADOOP_NEW_DB_URL,
            dict(name=er.target_name, location=location, if_not_exists=False))
    except Exception as e:
        raise Exception(f"Error while creating Database using Infra API: {e}")

    log_export_request_task(er.id, f"Database '{er.target_name}' created. "
                                   f"Now allocating rights "
                                   f"to {HIVE_EXPORTER_USER}.")

    try:
        post_hadoop(
            HADOOP_CHOWN_DB_URL,
            dict(location=location, uid=HIVE_EXPORTER_USER,
                 gid="hdfs", recursive=True))
    except Exception as e:
        raise Exception(f"Error while attributing rights on "
                        f"database '{er.target_name}' using Infra API: {e}")

    log_export_request_task(er.id, f"Database '{er.target_name}' "
                                   f"attributed to {HIVE_EXPORTER_USER} "
                                   f"and hdfs. Now asking for export.")


def prepare_for_export(er: ExportRequest):
    """
    If needed, do some preprocess for the data to be exported
    @param er:
    @return:
    """
    from exports.models import ExportType

    if er.output_format == ExportType.HIVE:
        prepare_hive_db(er)
    else:
        return


def post_export(er: ExportRequest) -> str:
    """
    Starts the job to realise the Export
    @param er:
    @return:
    """
    from exports.models import ExportType

    if er.output_format == ExportType.HIVE:
        task_id = post_export_hive(er)
    else:
        task_id = post_export_csv(er)

    return task_id


def conclude_export_hive(er: ExportRequest):
    """
    Allocates the owner of the export request ownership of the Database thas
    was created to receive the data from export
    @param er:
    @return:
    """
    location = build_location(er.target_name)
    log_export_request_task(
        er.id,
        f"Allocating database rights with name '{er.target_name} to user "
        f"{er.target_unix_account.name}'")

    try:
        post_hadoop(HADOOP_CHOWN_DB_URL,
                    dict(
                        location=location, uid=er.target_unix_account.name,
                        gid="hdfs", recursive=True))
    except Exception as e:
        raise Exception(f"Error while attributing rights on "
                        f"database '{er.target_name}' using Infra API: {e}")

    log_export_request_task(er.id, f"Database '{er.target_name}' attributed to "
                                   f"{er.target_unix_account.name}. "
                                   f"Conclusion finished.")


def conclude_export_csv(er: ExportRequest):
    return


def conclude_export(er: ExportRequest):
    """
    If needed, do some postprocess for the data that was exported
    @param er:
    @return:
    """
    from exports.models import ExportType

    if er.output_format == ExportType.HIVE:
        conclude_export_hive(er)
    else:
        conclude_export_csv(er)


# FHIR PERIMETERS #############################################################

FHIR_URL = env("FHIR_URL")


def get_fhir_organization_members(obj: dict) -> List[str]:
    # a member is expected to be like this:
    # { 'entity': { 'display' : 'Organizations-or-Group/id' }}
    members = obj.get("member", [])
    res = [
        o.get('entity') for o in members
        if isinstance(o, dict) and isinstance(o.get('entity'), dict)
    ]
    res = [o.get('display', "").split("/")[-1]
           for o in res
           if isinstance(o.get('display'), str)
           and o.get('display').startswith("Organization")]

    if not len(res):
        return []

    return res


def get_cohort_perimeters(cohort_id: int, token: str) -> List[str]:
    """
    Asks a remote API, that is used to generate OMOP cohorts,
    which perimeters are searched to build the cohort
    @param cohort_id: OMOP cohort id to analyse
    @param token: session token that is used to identify the user
    @return: list of perimeter ids
    """

    resp = requests.get(
        url=f"{FHIR_URL}/fhir/Group?_id={cohort_id}",
        headers={'Authorization': f"Bearer {token}"}
    )

    if resp.status_code == 401:
        raise ValidationError("Token error with FHIR api")

    try:
        res = resp.json()
    except Exception as e:
        raise Exception(f"Error: response from FHIR server not readable ({e})."
                        f"\nFull content: {resp.content}")

    if resp.status_code != 200:
        if resp.status_code == 500:
            issues = res.get('issue', [])
            if not len(issues) or not isinstance(issues[0], dict):
                err = f'could not read FHIR response: {str(res)}'
            else:
                issue = issues[0]
                err = issue.get(
                    'diagnostics', 'could not read FHIR response: ' + str(res)
                )
            raise ValidationError(f"Error with FHIR api checking: {err}")

        raise ValidationError(
            f"Error {resp.status_code} with FHIR api checking: {res['error']}. "
            f"Url called: {resp.url}"
        )

    entry = res.get('entry', [])
    if not len(entry):
        raise ValidationError(
            f"Entry field is empty on FHIR response, it means the provider "
            f"has no right on the cohort '{cohort_id}'."
        )
    if not isinstance(entry[0], dict):
        raise ValidationError(
            f"Could not read FHIR response, missing entry field: {str(res)}"
        )

    resource = entry[0].get('resource', None)
    if not isinstance(resource, dict):
        raise ValidationError(
            f"Could not read FHIR response, missing resource "
            f"field in entry: {str(res)}"
        )

    parent_perim_ids = get_fhir_organization_members(resource)

    if not len(parent_perim_ids):
        raise ValidationError(
            f"Could not read FHIR response, no member found with "
            f"entity.display starting with 'Organization' in resource: "
            f"{prettify_dict(resource)}.\n Full response : {prettify_dict(res)}"
        )

    return parent_perim_ids


# FILES EXTRACT ###############################################################

HDFS_SERVERS = env("HDFS_SERVERS").split(',')


HDFS_CLIENTS_DICT = {
    'current': HDFS_SERVERS[0],
    HDFS_SERVERS[0]: KerberosClient(HDFS_SERVERS[0])
}


def try_other_hdfs_servers():
    for server in [s for s in HDFS_SERVERS
                   if s != HDFS_CLIENTS_DICT['current']]:
        cl = KerberosClient(server)

        try:
            cl.status('/')
        except HdfsError:
            continue
        else:
            HDFS_CLIENTS_DICT[server] = KerberosClient(server)
            HDFS_CLIENTS_DICT['current'] = server
            return cl

    raise HdfsServerUnreachableError()


def get_client():
    cl = HDFS_CLIENTS_DICT.get(HDFS_CLIENTS_DICT['current'])
    try:
        cl.status('/')
    except HdfsError:
        return try_other_hdfs_servers()
    else:
        return cl


def build_path(file_name: str) -> str:
    return file_name


def stream_gen(file_name: str):
    file_path = build_path(file_name)
    with get_client().read(
            hdfs_path=file_path,
            offset=0,
            length=None,  # entire file
            # buffer_size=buffer_size,
            encoding=None,
            chunk_size=1000000,  # chunk_size,
            delimiter=None,
            progress=None
    ) as f:
        for chunk in f:
            yield chunk


def get_file_size(file_name: str) -> int:
    file_path = build_path(file_name)
    return get_client().status(file_path).get("length")


def delete_file(file_name: str):
    file_path = build_path(file_name)
    get_client().delete(file_path)
