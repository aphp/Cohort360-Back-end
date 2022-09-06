from django.db.models import Model
from rest_framework.request import Request

from admin_cohort.types import JobStatus
from cohort.FhirAPi import FhirCountResponse, FhirCohortResponse, \
    FhirValidateResponse


def format_json_request(json_req: str) -> str:
    """
    Called to format a json query stored in RequestQuerySnapshot
    to the format read by Fhir API
    :param json_req:
    :type json_req:
    :return:
    :rtype:
    """
    raise NotImplementedError()


def retrieve_perimeters(json_req: str) -> [str]:
    """
    Called to retrieve care_site_ids (perimeters) from a Json request
    :param json_req:
    :type json_req:
    :return:
    :rtype:
    """
    return None


def get_fhir_authorization_header(request: Request) -> dict:
    """
    Called when a request is about to be made to external Fhir API
    :param request:
    :type request:
    :return:
    :rtype:
    """
    raise NotImplementedError()


def cancel_job(job_id: str, auth_headers) -> JobStatus:
    """
    Sends a request to FHIR API to abort a job
    Its status will be then set to KILLED if it was not FINISHED already
    :param job_id:
    :type job_id:
    :param auth_headers:
    :type auth_headers:
    :return:
    :rtype:
    """
    raise NotImplementedError()


def post_count_cohort(
        json_file: str, auth_headers, log_prefix: str = "",
        dated_measure: Model = None
) -> FhirCountResponse:
    """
    Called to ask a Fhir API to compute the size of a cohort given
    the request in the json_file
    :param json_file:
    :type json_file:
    :param auth_headers:
    :type auth_headers:
    :param log_prefix:
    :type log_prefix: str
    :param dated_measure:
    :type dated_measure: DatedMeasure
    :return:
    :rtype:
    """
    raise NotImplementedError()


def post_create_cohort(
        json_file: str, auth_headers, log_prefix: str = "",
        cohort_result: Model = None
) -> FhirCohortResponse:
    """
    Called to ask a Fhir API to create a cohort given the request
    in the json_file
    :param json_file:
    :type json_file:
    :param auth_headers:
    :type auth_headers:
    :param log_prefix:
    :type log_prefix: str
    :param cohort_result:
    :type cohort_result: CohortResult
    :return:
    :rtype:
    """
    raise NotImplementedError()


def post_validate_cohort(json_file: str, auth_headers) -> FhirValidateResponse:
    """
    Called to ask a Fhir API to validate the format of the json_file
    :param json_file:
    :type json_file:
    :param auth_headers:
    :type auth_headers:
    :return:
    :rtype:
    """
    raise NotImplementedError()
