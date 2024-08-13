from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import viewsets

from admin_cohort.models import ReleaseNote
from admin_cohort.permissions import IsAuthenticated
from admin_cohort.serializers import ReleaseNoteSerializer


extended_schema = extend_schema(tags=["Release Notes"])


@extend_schema_view(
    list=extended_schema,
    retrieve=extended_schema,
    create=extended_schema,
    partial_update=extended_schema
)
class ReleaseNotesViewSet(viewsets.ModelViewSet):
    queryset = ReleaseNote.objects.all()
    serializer_class = ReleaseNoteSerializer
    http_method_names = ["post", "get", "patch"]
    search_fields = ["title", "message"]
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        return super(ReleaseNotesViewSet, self).get_queryset()\
                                               .order_by("-insert_datetime")
