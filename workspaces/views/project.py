from rest_framework import viewsets

from exports.permissions import can_user_read_datalabs
from admin_cohort.permissions import user_is_authenticated
from workspaces.models.project import Project
from workspaces.serializers import ProjectSerializer, PublicProjectSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    queryset = Project.objects.all()
    lookup_field = "id"
    http_method_names = ["get"]
    swagger_tags = ['Workspaces - projects']

    def get_serializer_class(self):
        if user_is_authenticated(self.request.user) and can_user_read_datalabs(self.request.user):
            return ProjectSerializer
        else:
            return PublicProjectSerializer
