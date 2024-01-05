from django.urls import path, include
from rest_framework.routers import DefaultRouter

from exports.views import ExportRequestViewSet, CohortViewSet, FhirFilterViewSet, ExportViewSet, ExportTableViewSet, ExportResultStatViewSet, \
                          DatalabViewSet, InfrastructureProviderViewSet
from exports.views.unix_account import UnixAccountViewSet


router = DefaultRouter()
router.register(r'unix-accounts', UnixAccountViewSet, basename="unix-accounts")
router.register(r'cohorts', CohortViewSet, basename="cohorts")
router.register(r'fhir-filters', FhirFilterViewSet, basename="fhir-filters")
router.register(r'', ExportRequestViewSet, basename="exports")

router_v1 = DefaultRouter()
router_v1.register(r'datalabs', DatalabViewSet, basename="datalabs")
router_v1.register(r'infrastructure_providers', InfrastructureProviderViewSet, basename="infrastructure_providers")
router_v1.register(r'export_stats', ExportResultStatViewSet, basename="export_stats")
router_v1.register(r'export_tables', ExportTableViewSet, basename="export_tables")
router_v1.register(r'exports', ExportViewSet, basename="exports")

urlpatterns = [path('', include(router.urls)),
               path('v1/', include((router_v1.urls, 'exports'), namespace="v1"))]
