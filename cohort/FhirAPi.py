from admin_cohort.models import JobStatus


class FhirValidateResponse:
    def __init__(
            self, success: bool = False, err_msg: str = "",
            fhir_job_status: JobStatus = JobStatus.UNKNOWN,
    ):
        self.success = success
        self.err_msg = err_msg
        self.fhir_job_status = fhir_job_status


class FhirCountResponse(FhirValidateResponse):
    def __init__(
            self, count: int = None, count_male: int = None,
            count_unknown: int = None, count_deceased: int = None,
            count_alive: int = None, count_female: int = None,
            count_min: int = None, count_max: int = None,
            fhir_datetime=None, fhir_job_id: str = "", job_duration=None,
            success: bool = False, err_msg: str = "",
            fhir_job_status: JobStatus = JobStatus.UNKNOWN,
    ):
        super(FhirCountResponse, self).__init__(
            success=success, err_msg=err_msg, fhir_job_status=fhir_job_status
        )
        self.count = count
        self.count_male = count_male
        self.count_unknown = count_unknown
        self.count_deceased = count_deceased
        self.count_alive = count_alive
        self.count_female = count_female
        self.count_min = count_min
        self.count_max = count_max
        self.fhir_datetime = fhir_datetime
        self.job_duration = job_duration
        self.fhir_job_id = fhir_job_id
        self.fhir_job_status = fhir_job_status


class FhirCohortResponse(FhirCountResponse):
    def __init__(
            self, count: int = None, group_id: str = "", fhir_datetime=None,
            fhir_job_id: str = "", job_duration=None, success: bool = False,
            err_msg: str = "", fhir_job_status: JobStatus = JobStatus.UNKNOWN,

    ):
        super(FhirCohortResponse, self).__init__(
            count=count, fhir_datetime=fhir_datetime, fhir_job_id=fhir_job_id,
            job_duration=job_duration, success=success, err_msg=err_msg,
            fhir_job_status=fhir_job_status
        )
        self.group_id = group_id
