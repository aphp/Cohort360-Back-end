from django.db.models import QuerySet
from rest_framework import viewsets

from admin_cohort.models import ReleaseNote
from admin_cohort.permissions import IsAuthenticated
from admin_cohort.serializers import ReleaseNoteSerializer


class ReleaseNotesViewSet(viewsets.ModelViewSet):
    queryset = ReleaseNote.objects.all()
    serializer_class = ReleaseNoteSerializer
    http_method_names = ["post", "get", "patch"]
    search_fields = ["title", "message"]
    permission_classes = [IsAuthenticated]
    swagger_tags = ["Release Notes"]

    def get_queryset(self) -> QuerySet:
        return super(ReleaseNotesViewSet, self).get_queryset()\
                                               .order_by("-insert_datetime")
