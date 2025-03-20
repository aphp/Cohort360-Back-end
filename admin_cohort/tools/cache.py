import logging

from django.core.cache import cache
from django.core.cache.backends.dummy import DummyCache
from rest_framework_extensions.cache.decorators import CacheResponse


_logger = logging.getLogger("info")


class CustomCacheResponse(CacheResponse):
    def process_cache_response(self, view_instance, view_method, request, args, kwargs):
        response = super(CustomCacheResponse, self).process_cache_response(view_instance, view_method, request, args, kwargs)
        return response


cache_response = CustomCacheResponse


def construct_cache_key(view_instance=None, view_method=None, request=None, *args, **kwargs):
    session_id = None
    if hasattr(request, "session"):
        session_id = request.session.session_key
    username = request.user.username
    view_class = view_instance.__class__.__name__
    view_meth_name = view_method.__name__
    keys = (username, view_class, view_meth_name, request._request.path)
    if session_id is not None:
        keys += (session_id,) + keys
    key = ".".join(keys)

    if request.query_params:
        key = f"{key}." + ".".join(map(str, (f"{k}={v}" for k, v in request.query_params.items())))
    return key


def invalidate_cache(model_name: str, user: str = "*"):
    view_name = f"*{model_name}ViewSet"
    key = f"*{user}.{view_name}.*"
    cache.delete_pattern(key)


class CustomDummyCache(DummyCache):
    def delete_pattern(self, key, version=None):
        return False
