from django.utils import timezone
from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets


class BaseViewset(viewsets.ModelViewSet):
    def get_serializer_context(self):
        return {'request': self.request}

    def perform_destroy(self, instance):
        instance.delete_datetime = timezone.now()
        instance.save()


# seen on https://stackoverflow.com/a/64440802
class CustomAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        tags = self.overrides.get('tags', None) \
               or getattr(self.view, 'swagger_tags', [])
        if not tags:
            tags = [operation_keys[0]]

        return tags


class YarnReadOnlyViewsetMixin:
    @swagger_auto_schema(auto_schema=None)
    def create(self, request, *args, **kwargs):
        super(YarnReadOnlyViewsetMixin, self).create(self, request, *args,
                                                     **kwargs)

    @swagger_auto_schema(auto_schema=None)
    def destroy(self, request, *args, **kwargs):
        super(YarnReadOnlyViewsetMixin, self).destroy(self, request, *args,
                                                      **kwargs)

    @swagger_auto_schema(auto_schema=None)
    def partial_update(self, request, *args, **kwargs):
        super(YarnReadOnlyViewsetMixin, self).partial_update(self, request,
                                                             *args, **kwargs)

    @swagger_auto_schema(auto_schema=None)
    def update(self, request, *args, **kwargs):
        super(YarnReadOnlyViewsetMixin, self).update(self, request, *args,
                                                     **kwargs)
