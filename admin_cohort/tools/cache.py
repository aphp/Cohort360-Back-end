import logging

from django.core.cache import cache
from django.core.cache.backends.dummy import DummyCache
from django.utils.cache import patch_vary_headers
from rest_framework_extensions.cache.decorators import CacheResponse


_logger = logging.getLogger("info")

RETRIEVE_ACTION = "retrieve"


class CustomCacheResponse(CacheResponse):
    def process_cache_response(self, view_instance, view_method, request, args, kwargs):
        response = super(CustomCacheResponse, self).process_cache_response(view_instance, view_method, request, args, kwargs)
        patch_vary_headers(response, ['SESSION_ID'])
        return response


cache_response = CustomCacheResponse


def construct_cache_key(view_instance=None, view_method=None, request=None, *args, **kwargs):
    username = request.user.provider_username
    view_class = view_instance.__class__.__name__
    view_meth_name = view_method.__name__
    key = ".".join((username, view_class, view_meth_name))

    if view_instance.detail:
        lookup_field = view_instance.lookup_field
        record_id = view_instance.kwargs.get(lookup_field)
        key = ".".join((key, lookup_field, record_id))
    if request.query_params:
        key = f"{key}." + ".".join(map(str, (f"{k}={v}" for k, v in request.query_params.items())))
    return key


def invalidate_cache(model_name: str, user: str = "*"):
    view_name = f"*{model_name}ViewSet"
    key = f"{user}.{view_name}.*"
    count = cache.delete_pattern(key)
    _logger.info(f"Cache invalidated: deleted {count} records matching '*{key}*'")


class CustomDummyCache(DummyCache):
    def delete_pattern(self, key, version=None):
        return False
