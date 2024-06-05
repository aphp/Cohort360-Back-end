import functools

from django.core.cache import cache


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
