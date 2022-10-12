from django.urls import include, path

from rest_framework import routers
from rest_framework_extensions.routers import NestedRouterMixin

from accesses.views import NestedPerimeterViewSet, PerimeterViewSet, \
    AccessViewSet, RoleViewSet, ProfileViewSet


class NestedDefaultRouter(NestedRouterMixin, routers.DefaultRouter):
    pass


router = NestedDefaultRouter()
router.register(r'accesses', AccessViewSet, basename="accesses")
router.register(r'roles', RoleViewSet, basename="roles")
router.register(r'profiles', ProfileViewSet, basename="profiles")

p_router = router.register(r'perimeters', PerimeterViewSet, basename="perimeters")
p_router.register('children', NestedPerimeterViewSet, basename="perimeter-children", parents_query_lookups=["parent"])

urlpatterns = [path('', include(router.urls))]
