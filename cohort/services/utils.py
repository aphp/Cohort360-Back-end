import functools
import logging
from enum import StrEnum
from smtplib import SMTPException
from typing import Callable

from django.core.cache import cache
from rest_framework.request import Request

from admin_cohort.middleware.request_trace_id_middleware import add_trace_id
from cohort.models import FeasibilityStudy


_logger = logging.getLogger('django.request')


class ServerError(Exception):
    pass


def await_celery_task(func):

    def retrieve_lock(lock_id: str):
        return cache.get(lock_id)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        dm_id = kwargs.get("uuid")
        lock = retrieve_lock(lock_id=dm_id)
        while lock is not None:
            lock = retrieve_lock(lock_id=dm_id)
        return func(*args, **kwargs)
    return wrapper


def locked_instance_task(task):
    def acquire_lock(lock_id: str):
        return cache.add(lock_id, lock_id, 5*60)

    def release_lock(lock_id: str):
        cache.delete(lock_id)

    @functools.wraps(task)
    def wrapper(*args, **kwargs):
        instance_id = kwargs.get("dm_uuid")
        locked = acquire_lock(instance_id)
        if locked:
            try:
                task(*args, **kwargs)
            finally:
                release_lock(instance_id)
    return wrapper


def get_feasibility_study_by_id(fs_id: str) -> FeasibilityStudy:
    return FeasibilityStudy.objects.get(pk=fs_id)


def send_email_notification(notification: Callable, **kwargs) -> None:
    try:
        notification(**kwargs)
    except (ValueError, SMTPException) as e:
        _logger.exception(f"FeasibilityStudy[{kwargs.get('fs_id')}] Couldn't send email notification: {e}")


def get_authorization_header(request: Request) -> dict:
    headers = {"Authorization": f"Bearer {request.META.get('HTTP_AUTHORIZATION')}",
               "authorizationMethod": request.META.get('HTTP_AUTHORIZATIONMETHOD')
               }
    headers = add_trace_id(headers)
    return headers


class RefreshFrequency(StrEnum):
    DAILY = 'daily'
    EVER_OTHER_DAY = 'ever_other_day'
    WEEKLY = 'weekly'
