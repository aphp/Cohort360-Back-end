from django.urls import include, path

from accesses.views import NestedPerimeterViewSet, PerimeterViewSet, AccessViewSet, RoleViewSet, ProfileViewSet
from admin_cohort.urls import NestedDefaultRouter


router = NestedDefaultRouter()
router.register(r'accesses', AccessViewSet, basename="accesses")
router.register(r'roles', RoleViewSet, basename="roles")
router.register(r'profiles', ProfileViewSet, basename="profiles")

p_router = router.register(r'perimeters', PerimeterViewSet, basename="perimeters")
p_router.register('children', NestedPerimeterViewSet, basename="perimeter-children", parents_query_lookups=["parent"])

urlpatterns = [path('', include(router.urls))]
