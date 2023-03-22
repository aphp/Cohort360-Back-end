import logging
from functools import wraps

from django.core.cache import cache
from django.utils.cache import patch_vary_headers
from rest_framework.response import Response

from accesses.apps import AccessConfig
from admin_cohort.models import User

_logger = logging.getLogger("info")

CACHED_ENDPOINTS = ("my_accesses", "my_rights")
CACHE_AGE = 24 * 60 * 60


def get_cache_key(endpoint_name: str, user: User):
    return f"{AccessConfig.name}_{endpoint_name}_{user.provider_username}"


def do_cache_response(response: Response, cache_key: str):
    patch_vary_headers(response, ['SESSION_ID'])
    cache.set(cache_key, response, CACHE_AGE)


def invalidate_cache(user: User):
    cache_keys = [get_cache_key(endpoint_name=endpoint_name, user=user) for endpoint_name in CACHED_ENDPOINTS]
    cache.delete_many(cache_keys)
    _logger.info(f"Cache flushed for user {user}")


def cache_view_response(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        cache_key = get_cache_key(endpoint_name=view_func.__qualname__, user=request.user)
        if cache.get(cache_key):
            return cache.get(cache_key)
        response = view_func(request, *args, **kwargs)
        do_cache_response(response, cache_key)
        return response
    return wrapper
