from django.utils import timezone
from rest_framework import viewsets

from admin_cohort.tools.swagger import SchemaMeta


class BaseViewSet(viewsets.ModelViewSet, metaclass=SchemaMeta):
    swagger_tags = []

    def get_serializer_context(self):
        return {'request': self.request}

    def perform_destroy(self, instance):
        instance.delete_datetime = timezone.now()
        instance.save()
