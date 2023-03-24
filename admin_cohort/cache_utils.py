import logging

from django.core.cache import cache
from django.core.cache.backends.dummy import DummyCache
from django.utils.cache import patch_vary_headers
from rest_framework.views import APIView
from rest_framework_extensions.cache.decorators import CacheResponse

from admin_cohort.models import User

_logger = logging.getLogger("info")

RETRIEVE_ACTION = "retrieve"


class CustomCacheResponse(CacheResponse):
    def process_cache_response(self, view_instance, view_method, request, args, kwargs):
        response = super(CustomCacheResponse, self).process_cache_response(view_instance, view_method, request, args, kwargs)
        patch_vary_headers(response, ['SESSION_ID'])
        return response


cache_response = CustomCacheResponse


def construct_cache_key(view_instance=None, view_method=None, request=None, *args, **kwargs):
    key = f"{request.user.provider_username}.{view_instance.__class__.__name__}.{view_method.__name__}"
    if view_instance.action == RETRIEVE_ACTION:
        lookup_field = view_instance.lookup_field
        record_id = view_instance.kwargs.get(lookup_field)
        key = f"{key}.{lookup_field}.{record_id}"
    return key


def invalidate_cache(view_instance: APIView, user: User):
    user_viewset_keys = f"{user.provider_username}.{view_instance.__class__.__name__}.*"
    cache.delete_pattern(user_viewset_keys)
    _logger.info(f"Cache flushed for user {user} on ViewSet {view_instance.__class__.__name__}")


class CustomDummyCache(DummyCache):
    def delete_pattern(self, key, version=None):
        return False
