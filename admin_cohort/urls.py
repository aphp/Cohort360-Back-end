from django.conf.urls.static import static
from django.urls import include, path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import routers, permissions
from rest_framework.routers import SimpleRouter
from rest_framework_extensions.routers import NestedRouterMixin

from . import __version__, __title__, settings
from admin_cohort.views import OIDCLoginView, UserViewSet, RequestLogViewSet, MaintenancePhaseViewSet, CacheViewSet, ReleaseNotesViewSet, \
    JWTLoginView, TokenRefreshView, LogoutView

schema_view = get_schema_view(info=openapi.Info(title=__title__,
                                                default_version=f'v{__version__}',
                                                description="Portail and Cohort360 API",
                                                terms_of_service=""),
                              public=True,
                              permission_classes=[permissions.AllowAny])


class NestedDefaultRouter(NestedRouterMixin, routers.DefaultRouter):
    pass


router = SimpleRouter()
router.register(r'maintenances', MaintenancePhaseViewSet, basename="maintenances")
router.register(r'users', UserViewSet, basename="users")
router.register(r'logs', RequestLogViewSet, basename="logs")
router.register(r'release-notes', ReleaseNotesViewSet, basename="release_notes")

urlpatterns = [re_path(r'^auth/oidc/login', OIDCLoginView.as_view(), name='oidc-login'),
               re_path(r'^auth/login/$', JWTLoginView.as_view(), name='jwt-login'),
               re_path(r'^auth/logout/$', LogoutView.as_view(), name='logout'),
               re_path(r'^auth/refresh/$', TokenRefreshView.as_view(), name='token-refresh'),
               re_path(r'^cache', CacheViewSet.as_view(), name='cache'),
               re_path(r"^docs", schema_view.with_ui(renderer="swagger", cache_timeout=0, )),
               re_path(r"^redoc/$", schema_view.with_ui(renderer="redoc", cache_timeout=0), name="schema-redoc"),
               re_path(r'^', include(router.urls)),
               path("accesses/", include(("accesses.urls", "accesses"), namespace="accesses")),
               path("cohort/", include(("cohort.urls", "cohort"), namespace="cohort")),
               path("exports/", include(("exports.urls", "exports"), namespace="exports")),
               ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
