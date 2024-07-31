from django.http import QueryDict
from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import status
from rest_framework_extensions.mixins import NestedViewSetMixin

from admin_cohort.tools.cache import cache_response
from cohort.models import Request
from cohort.serializers import RequestSerializer, RequestCreateSerializer, RequestPatchSerializer
from cohort.views.shared import UserObjectsRestrictedViewSet


@extend_schema_view(
    list=extend_schema(responses={status.HTTP_200_OK: RequestSerializer(many=True)}),
    retrieve=extend_schema(responses={status.HTTP_200_OK: RequestSerializer}),
    create=extend_schema(request=RequestCreateSerializer,
                         responses={status.HTTP_201_CREATED: RequestSerializer}),
    partial_update=extend_schema(request=RequestPatchSerializer,
                                 responses={status.HTTP_200_OK: RequestSerializer}),
    destroy=extend_schema(responses={status.HTTP_204_NO_CONTENT: None})
)
class RequestViewSet(NestedViewSetMixin, UserObjectsRestrictedViewSet):
    queryset = Request.objects.all()
    serializer_class = RequestSerializer
    http_method_names = ["get", "post", "patch", "delete"]
    search_fields = ("$name", "$description",)
    swagger_tags = ["Requests"]

    @cache_response()
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class NestedRequestViewSet(RequestViewSet):

    def create(self, request, *args, **kwargs):
        if type(request.data) is QueryDict:
            request.data._mutable = True
        if 'parent_folder' in kwargs:
            request.data["parent_folder"] = kwargs['parent_folder']
        return super().create(request, *args, **kwargs)
