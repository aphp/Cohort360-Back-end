from typing import List

from admin_cohort.models import NewJobStatus
from exports.models import ExportRequest


# EXPORTS JOBS ################################################################

class ApiJobResponse:
    def __init__(self, status: NewJobStatus, output: str = "", err: str = ""):
        self.status: NewJobStatus = status
        self.output: str = output
        self.err: str = err

    @property
    def has_ended(self):
        return self.status in [NewJobStatus.failed, NewJobStatus.cancelled,
                               NewJobStatus.finished, NewJobStatus.unknown]


def get_job_status(er: ExportRequest) -> ApiJobResponse:
    """
    Returns the status of the job of the ExpRequest, and returns it
    using ApiJobResponse format, providing also output and/or error messages
    @param er: ExpRequest to get info about
    @return: ApiJobResponse: info about the job
    """
    raise NotImplementedError()


def post_export(er: ExportRequest) -> str:
    """
    Starts the job to realise the Export
    @param er:
    @return:
    """
    raise NotImplementedError()


def prepare_for_export(er: ExportRequest) -> str:
    """
    If needed, do some preprocess for the data to be exported
    @param er:
    @return:
    """
    raise NotImplementedError()


def conclude_export(er: ExportRequest) -> str:
    """
    If needed, do some postprocess for the data that was exported
    @param er:
    @return:
    """
    raise NotImplementedError()


# FHIR PERIMETERS #############################################################

def get_cohort_perimeters(cohort_id: int, token: str) -> List[str]:
    """
    Asks a remote API, that is used to generate OMOP cohorts,
    which perimeters are searched to build the cohort
    @param cohort_id: OMOP cohort id to analyse
    @param token: session token that is used to identify the user
    @return: list of perimeter ids
    """
    raise NotImplementedError()


# FILES EXTRACT ###############################################################

def stream_gen(file_name: str):
    raise NotImplementedError()
    # with get_client().read() as f:
    #     for chunk in f:
    #         yield chunk


def get_file_size(file_name: str) -> int:
    raise NotImplementedError()


def delete_file(file_name: str):
    raise NotImplementedError()
