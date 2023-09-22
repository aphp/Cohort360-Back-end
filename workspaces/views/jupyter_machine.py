from rest_framework import viewsets

from workspaces.models.jupyter_machine import JupyterMachine
from workspaces.permissions import AccountPermissions
from workspaces.serializers import JupyterMachineSerializer


class JupyterMachineViewSet(viewsets.ModelViewSet):
    serializer_class = JupyterMachineSerializer
    queryset = JupyterMachine.objects.all()
    lookup_field = "id"
    http_method_names = ["get"]
    permission_classes = [AccountPermissions]

    swagger_tags = ['Workspaces - jupyter-machines']
