from django.utils import timezone
from rest_framework import viewsets


class BaseViewSet(viewsets.ModelViewSet):
    def get_serializer_context(self):
        return {'request': self.request}

    def perform_destroy(self, instance):
        instance.delete_datetime = timezone.now()
        instance.save()
