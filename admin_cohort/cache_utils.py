import logging

from django.core.cache import cache
from django.utils.cache import patch_vary_headers
from rest_framework.views import APIView
from rest_framework_extensions.cache.decorators import CacheResponse

from admin_cohort.models import User

_logger = logging.getLogger("info")

CACHED_ENDPOINTS = ("my_accesses", "my_rights")
CACHE_AGE = 24 * 60 * 60


class CustomCacheResponse(CacheResponse):
    def process_cache_response(self, view_instance, view_method, request, args, kwargs):
        response = super(CustomCacheResponse, self).process_cache_response(view_instance, view_method, request, args, kwargs)
        patch_vary_headers(response, ['SESSION_ID'])
        return response


cache_response = CustomCacheResponse


def construct_cache_key(view_instance=None, view_method=None, request=None, *args, **kwargs):
    view_method_name = view_method and view_method.__name__ or kwargs.get("view_method_name")
    user = request and request.user or kwargs.get("user")
    return f"{view_instance.__class__.__name__}.{view_method_name}.{user.provider_username}"


def invalidate_cache(view_instance: APIView, user: User):
    cache_keys = [construct_cache_key(view_instance=view_instance, **dict(view_method_name=endpoint_name, user=user))
                  for endpoint_name in CACHED_ENDPOINTS]
    cache.delete_many(cache_keys)
    _logger.info(f"Cache flushed for user {user}")
