from django.http import QueryDict
from rest_framework import viewsets
from rest_framework.relations import RelatedField

from admin_cohort.tools.negative_limit_paginator import NegativeLimitOffsetPagination
from admin_cohort.tools.request_log_mixin import RequestLogMixin
from admin_cohort.tools.swagger import SchemaMeta
from cohort.permissions import IsOwnerPermission


class UserObjectsRestrictedViewSet(RequestLogMixin, viewsets.ModelViewSet, metaclass=SchemaMeta):
    lookup_field = "uuid"
    permission_classes = (IsOwnerPermission,)
    pagination_class = NegativeLimitOffsetPagination
    logging_methods = ['POST', 'PATCH', 'DELETE']
    swagger_tags = []

    def get_serializer_context(self):
        return {'request': self.request}

    def get_queryset(self):
        return self.__class__.queryset.filter(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        if type(request.data) is QueryDict:
            request.data._mutable = True
        request.data['owner'] = request.data.get('owner', request.user.pk)
        return super().create(request, *args, **kwargs)

    # todo : remove when front is ready
    #  (front should not post with '_id' fields)
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        s = self.get_serializer_class()()
        primary_key_fields = [f.field_name for f in s._writable_fields if isinstance(f, RelatedField)]

        if isinstance(request.data, QueryDict):
            request.data._mutable = True

        for field_name in primary_key_fields:
            field_name_with_id = f'{field_name}_id'
            if field_name_with_id in request.data:
                request.data[field_name] = request.data[field_name_with_id]
