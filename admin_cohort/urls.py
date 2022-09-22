from django.conf.urls import url
from django.conf.urls.static import static
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import routers, permissions
from rest_framework_extensions.routers import NestedRouterMixin

from accesses.views import AccessViewSet, RoleViewSet, ProfileViewSet, \
    PerimeterViewSet, NestedPerimeterViewSet
from . import __version__, __title__, settings
from .views import UserViewSet, LoggingViewset, MaintenancePhaseViewSet

schema_view = get_schema_view(
    openapi.Info(
        title=__title__,
        default_version=f'v{__version__}',
        description="Infos de l'API concernant le portail d'administration",
        terms_of_service="",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


class NestedDefaultRouter(NestedRouterMixin, routers.DefaultRouter):
    pass


router = NestedDefaultRouter()
router.register(r'maintenances',
                MaintenancePhaseViewSet, basename="maintenances")
router.register(r'users', UserViewSet, basename="users")
router.register(r'logs', LoggingViewset, basename="logs")
# router.register(r'care-sites', PerimeterViewSet, basename="care-sites")
# router.register(r'providers', UserViewSet, basename="providers")

router.register(r'accesses', AccessViewSet, basename="accesses")
router.register(r'roles', RoleViewSet, basename="roles")
router.register(r'profiles', ProfileViewSet, basename="profiles")

p_router = router.register(
    r'perimeters', PerimeterViewSet, basename="perimeters")
p_router.register(
    'children',
    NestedPerimeterViewSet,
    basename="perimeter-children",
    parents_query_lookups=["parent"],
)

internal_urls = []


urlpatterns = [
    url(r'^', include(router.urls)),
                  path("accounts/", include("admin_cohort.urls_login")),
                  path("accesses/",
                       include(("accesses.urls", "accesses"), namespace="accesses")),
                  path("cohort/", include(("cohort.urls", "cohort"), namespace="cohort")),
                  path("exports/", include(("exports.urls", "exports"), namespace="exports")),
                  path("workspaces/",
                       include(("workspaces.urls", "workspaces"), namespace="workspaces")),
                  url(r"^docs", schema_view.with_ui("swagger", cache_timeout=0, )),
                  url(r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0),
                      name="schema-redoc"),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
