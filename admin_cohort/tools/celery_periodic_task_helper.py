import functools
import logging

from django.core.cache import cache

LOCK_EXPIRE = 60 * 5  # Lock expires in 5 minutes

logger = logging.getLogger("info")


def ensure_single_task(task_name: str):
    def ensure_single_task_decorator(func):
        @functools.wraps(func)
        def wrapper_task(*args, **kwargs):
            lock_id = "%s-lock" % task_name

            # cache.add fails if if the key already exists
            def acquire_lock():
                return cache.add(lock_id, "true", LOCK_EXPIRE)

            def release_lock():
                cache.delete(lock_id)

            if acquire_lock():
                try:
                    func(*args, **kwargs)
                finally:
                    release_lock()
            else:
                logger.info(f"Task already {task_name} run by another worker")

        return wrapper_task

    return ensure_single_task_decorator
