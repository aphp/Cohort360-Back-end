from django.urls import include, path

from rest_framework import routers

from workspaces.views import AccountViewset, ProjectViewset, \
    JupyterMachineViewset, RangerHivePolicyViewset, LdapGroupViewset, \
    KernelViewset

router = routers.DefaultRouter()
router.register(r'projects', ProjectViewset, basename="projects")
router.register(r'users', AccountViewset, basename="accounts")
router.register(r'jupyter-machines', JupyterMachineViewset, basename="jupyter-machines")
router.register(r'ranger-hive-policies', RangerHivePolicyViewset, basename="ranger-hive-policies")
router.register(r'ldap-groups', LdapGroupViewset, basename="ldap-groups")
router.register(r'kernels', KernelViewset, basename="kernels")

urlpatterns = [path('', include(router.urls))]
