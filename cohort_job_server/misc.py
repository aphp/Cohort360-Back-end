import logging


JOB_STATUS = "request_job_status"
GROUP_ID = "group.id"
GROUP_COUNT = "group.count"
COUNT = "count"
MAXIMUM = "maximum"
MINIMUM = "minimum"
ERR_MESSAGE = "message"
EXTRA = "extra"

_celery_logger = logging.getLogger('celery.app')
_logger_err = logging.getLogger("django.request")
_logger = logging.getLogger('info')


def log_message(msg: str):
    _celery_logger.info(msg)


def log_feasibility_study_task(fs_uuid: str, msg: str):
    log_message(f"FeasibilityStudy Task [FS: {fs_uuid}] {msg}")


def log_count_task(dm_uuid: str, msg: str):
    log_message(f"Count Task [DM: {dm_uuid}] {msg}")


def log_count_all_task(dm_uuid: str, msg: str):
    log_message(f"Global Count Task [DM: {dm_uuid}] {msg}")


def log_create_task(cr_uuid: str, msg):
    log_message(f"Cohort Create Task [CR: {cr_uuid}] {msg}")
