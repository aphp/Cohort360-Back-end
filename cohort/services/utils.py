import functools
import logging
from enum import StrEnum
from smtplib import SMTPException
from time import sleep
from typing import Callable

from django.core.cache import cache
from rest_framework.request import Request

from cohort.models import FeasibilityStudy


_logger = logging.getLogger('django.request')


class ServerError(Exception):
    pass


def await_celery_task(func):

    def retrieve_lock(lock_id: str):
        return cache.get(lock_id)

    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        dm_id = kwargs.get("uuid")
        lock = retrieve_lock(lock_id=dm_id)
        while lock is not None:
            sleep(0.5)
            lock = retrieve_lock(lock_id=dm_id)
        return func(request, *args, **kwargs)
    return wrapper


def locked_instance_task(task):
    def acquire_lock(lock_id: str):
        return cache.add(lock_id, lock_id, 5*60)

    def release_lock(lock_id: str):
        cache.delete(lock_id)

    @functools.wraps(task)
    def wrapper(*args, **kwargs):
        instance_id = kwargs.get("dm_id")
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
    return headers


class RefreshFrequency(StrEnum):
    DAILY = 'daily'
    EVERY_OTHER_DAY = 'every_other_day'
    WEEKLY = 'weekly'
