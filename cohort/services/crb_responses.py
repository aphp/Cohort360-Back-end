from admin_cohort.types import JobStatus


class CRBResponse:
    def __init__(self, success: bool = False, err_msg: str = "", fhir_job_status: JobStatus = JobStatus.new,
                 fhir_datetime=None, fhir_job_id: str = "", job_duration=None, count: int = None):
        self.success = success
        self.err_msg = err_msg
        self.fhir_job_status = fhir_job_status
        self.fhir_datetime = fhir_datetime
        self.fhir_job_id = fhir_job_id
        self.job_duration = job_duration
        self.count = count


class CRBCountResponse(CRBResponse):
    def __init__(self, count_min: int = None, count_max: int = None, **kwargs):
        super(CRBCountResponse, self).__init__(**kwargs)
        self.count_min = count_min
        self.count_max = count_max


class CRBCohortResponse(CRBResponse):
    # todo: 2b refactored as group.id no longer needed. we get it via the SJS and ETL callback
    def __init__(self, group_id: str = "", **kwargs):
        super(CRBCohortResponse, self).__init__(**kwargs)
        self.group_id = group_id
