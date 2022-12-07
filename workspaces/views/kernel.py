from rest_framework import viewsets

from admin_cohort.views import YarnReadOnlyViewsetMixin
from workspaces.models.kernel import Kernel
from workspaces.permissions import AccountPermissions
from workspaces.serializers import KernelSerializer


class KernelViewSet(YarnReadOnlyViewsetMixin, viewsets.ModelViewSet):
    serializer_class = KernelSerializer
    queryset = Kernel.objects.all()
    lookup_field = "id"
    http_method_names = ["get"]
    permission_classes = [AccountPermissions]

    swagger_tags = ['Workspaces - kernels']
