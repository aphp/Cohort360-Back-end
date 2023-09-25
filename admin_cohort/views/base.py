from django.utils import timezone
from drf_yasg.inspectors import SwaggerAutoSchema
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
