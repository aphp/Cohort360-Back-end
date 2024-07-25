from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework import routers
from rest_framework.routers import SimpleRouter
from rest_framework_extensions.routers import NestedRouterMixin

from admin_cohort.views import OIDCLoginView, UserViewSet, RequestLogViewSet, MaintenancePhaseViewSet, CacheViewSet, ReleaseNotesViewSet, \
    JWTLoginView, TokenRefreshView, LogoutView


class NestedDefaultRouter(NestedRouterMixin, routers.DefaultRouter):
    pass


router = SimpleRouter()
router.register(r'maintenances', MaintenancePhaseViewSet, basename="maintenances")
router.register(r'users', UserViewSet, basename="users")
router.register(r'logs', RequestLogViewSet, basename="logs")
router.register(r'release-notes', ReleaseNotesViewSet, basename="release_notes")

urlpatterns = [re_path(r'^auth/oidc/login', OIDCLoginView.as_view({'post': 'post'}), name='oidc-login'),
               re_path(r'^auth/login/$', JWTLoginView.as_view(), name='jwt-login'),
               re_path(r'^auth/logout/$', LogoutView.as_view(), name='logout'),
               re_path(r'^auth/refresh/$', TokenRefreshView.as_view(), name='token-refresh'),
               re_path(r'^cache', CacheViewSet.as_view(), name='cache'),
               re_path(r'^', include(router.urls)),
               path("accesses/", include(("accesses.urls", "accesses"), namespace="accesses")),
               path("cohort/", include(("cohort.urls", "cohort"), namespace="cohort")),
               path("exports/", include(("exports.urls", "exports"), namespace="exports")),

               re_path(r"^schema", SpectacularAPIView.as_view(), name='schema'),
               re_path(r"^docs", SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
               re_path(r"^redoc/$", SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

               ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
