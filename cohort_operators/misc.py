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
_logger = logging.getLogger('info')


def log_feasibility_study_task(fs_uuid, msg):
    _celery_logger.info(f"FeasibilityStudy Task [FS: {fs_uuid}] {msg}")


def log_count_task(dm_uuid, msg):
    _celery_logger.info(f"Count Task [DM: {dm_uuid}] {msg}")


def log_count_all_task(dm_uuid, msg):
    _celery_logger.info(f"Global Count Task [DM: {dm_uuid}] {msg}")


def log_create_task(cr_uuid, msg):
    _celery_logger.info(f"Cohort Create Task [CR: {cr_uuid}] {msg}")


def log_delete_task(cr_uuid, msg):
    _celery_logger.info(f"Cohort Delete Task [CR: {cr_uuid}] {msg}")
