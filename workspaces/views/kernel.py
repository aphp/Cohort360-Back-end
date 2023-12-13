from rest_framework import viewsets

from workspaces.models.kernel import Kernel
from workspaces.permissions import AccountsPermission
from workspaces.serializers import KernelSerializer


class KernelViewSet(viewsets.ModelViewSet):
    serializer_class = KernelSerializer
    queryset = Kernel.objects.all()
    lookup_field = "id"
    http_method_names = ["get"]
    permission_classes = [AccountsPermission]

    swagger_tags = ['Workspaces - kernels']
