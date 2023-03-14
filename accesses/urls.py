from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accesses.views import NestedPerimeterViewSet, PerimeterViewSet, AccessViewSet, RoleViewSet, ProfileViewSet


router = DefaultRouter()
router.register(r'accesses', AccessViewSet, basename="accesses")
router.register(r'roles', RoleViewSet, basename="roles")
router.register(r'profiles', ProfileViewSet, basename="profiles")

p_router = router.register(r'perimeters', PerimeterViewSet, basename="perimeters")
p_router.register('children', NestedPerimeterViewSet, basename="perimeter-children", parents_query_lookups=["parent"])

urlpatterns = [path('', include(router.urls))]
