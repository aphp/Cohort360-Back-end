from django.conf.urls import url
from django.urls import include, path
from drf_yasg import openapi
from . import __version__, __title__

from rest_framework import routers, permissions
from rest_framework_swagger.views import get_swagger_view
from drf_yasg.views import get_schema_view

from accesses.views import RoleViewSet, AccessViewSet, PerimeterViewSet, \
    ProfileViewSet
from .views import UserViewSet, LoggingViewset, maintenance_view, \
    MaintenancePhaseViewSet

router = routers.DefaultRouter()
router.register(r'accesses', AccessViewSet, basename="accesses")
router.register(r'maintenances',
                MaintenancePhaseViewSet, basename="maintenances")
router.register(r'perimeters', PerimeterViewSet, basename="perimeters")
router.register(r'users', UserViewSet, basename="users")
router.register(r'roles', RoleViewSet, basename="roles")
router.register(r'profiles', ProfileViewSet, basename="profiles")
router.register(r'logs', LoggingViewset, basename="logs")
router.register(r'care-sites', PerimeterViewSet, basename="care-sites")
router.register(r'providers', UserViewSet, basename="providers")

old_schema_view = get_swagger_view(title='Cohort360 API')

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

internal_urls = [
]

urlpatterns = [
    url(r'^', include(router.urls)),
    path(
        "workspaces/", include(
            ('workspaces.urls', 'workspaces'), namespace="workspaces"
        )
    ),
    path("exports/", include(('exports.urls', 'exports'), namespace="exports")),
    path("cohort/", include(('cohort.urls', 'cohort'), namespace="cohort")),
    path('accounts/', include('admin_cohort.urls_login')),
    url(r'^docs', schema_view.with_ui('swagger', cache_timeout=0, )),
    url(r'^old-docs', old_schema_view),
    # to deprecate
    url(r'maintenance', maintenance_view),
    url(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0),
        name='schema-redoc'),
]
