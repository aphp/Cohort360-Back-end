from django.urls import include, path
from rest_framework import routers

from workspaces.views import ProjectViewSet, JupyterMachineViewSet, AccountViewSet, LdapGroupViewSet, KernelViewSet, \
    RangerHivePolicyViewSet

router = routers.DefaultRouter()
router.register(r'projects', ProjectViewSet, basename="projects")
router.register(r'accounts', AccountViewSet, basename="accounts")
router.register(r'jupyter-machines', JupyterMachineViewSet, basename="jupyter-machines")
router.register(r'ranger-hive-policies', RangerHivePolicyViewSet, basename="ranger-hive-policies")
router.register(r'ldap-groups', LdapGroupViewSet, basename="ldap-groups")
router.register(r'kernels', KernelViewSet, basename="kernels")

urlpatterns = [path('', include(router.urls))]
