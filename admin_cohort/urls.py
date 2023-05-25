from django.conf.urls.static import static
from django.urls import include, path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import routers, permissions
from rest_framework_extensions.routers import NestedRouterMixin

from . import __version__, __title__, settings
from admin_cohort.views import OIDCTokensView, UserViewSet, LoggingViewset, MaintenancePhaseViewSet

schema_view = get_schema_view(openapi.Info(title=__title__,
                                           default_version=f'v{__version__}',
                                           description="Portail and Cohort360 API",
                                           terms_of_service=""),
                              public=True,
                              permission_classes=[permissions.AllowAny])


class NestedDefaultRouter(NestedRouterMixin, routers.DefaultRouter):
    pass


router = NestedDefaultRouter()
router.register(r'maintenances', MaintenancePhaseViewSet, basename="maintenances")
router.register(r'users', UserViewSet, basename="users")
router.register(r'logs', LoggingViewset, basename="logs")

urlpatterns = [re_path(r'^', include(router.urls)),
               re_path(r'^auth/oidc/login', OIDCTokensView.as_view({'post': 'post'}), name='oidc-login'),
               path("accounts/", include("admin_cohort.urls_login")),
               path("accesses/", include(("accesses.urls", "accesses"), namespace="accesses")),
               path("cohort/", include(("cohort.urls", "cohort"), namespace="cohort")),
               path("exports/", include(("exports.urls", "exports"), namespace="exports")),
               path("workspaces/", include(("workspaces.urls", "workspaces"), namespace="workspaces")),
               re_path(r"^docs", schema_view.with_ui("swagger", cache_timeout=0, )),
               re_path(r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
               ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
