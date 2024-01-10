import logging
from rest_framework.request import Request
from admin_cohort.settings import SJS_USERNAME, ETL_USERNAME


_celery_logger = logging.getLogger('celery.app')


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


def is_sjs_or_etl_user(request: Request):
    return request.method in ("GET", "PATCH") and \
           request.user.is_authenticated and \
           request.user.provider_username in [SJS_USERNAME, ETL_USERNAME]


def is_sjs_user(request: Request):
    return is_sjs_or_etl_user(request=request)
