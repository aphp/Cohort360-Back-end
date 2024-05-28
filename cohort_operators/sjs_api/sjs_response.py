from cohort_operators.sjs_api.status_mapper import status_mapper


class SJSResponse:
    def __init__(self, success: bool = False, err_msg: str = "", **kwargs):
        self.success = success
        self.err_msg = err_msg
        job_status = kwargs.get('status', '')
        self.job_status = status_mapper(job_status)
        if not self.job_status:
            raise ValueError(f"Invalid status value, got `{job_status}`")
        self.job_id = kwargs.get('jobId')
        self.message = kwargs.get('message', 'No message')
        self.stack = kwargs.get("stack", 'No stack')
