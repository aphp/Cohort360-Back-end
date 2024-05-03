from django.urls import path, include
from rest_framework.routers import DefaultRouter

from exports.views import CohortViewSet, FhirFilterViewSet, ExportViewSet, ExportResultStatViewSet, \
                          DatalabViewSet, InfrastructureProviderViewSet


router = DefaultRouter()
router.register(r'cohorts', CohortViewSet, basename="cohorts")
router.register(r'fhir-filters', FhirFilterViewSet, basename="fhir-filters")
router.register(r'datalabs', DatalabViewSet, basename="datalabs")
router.register(r'infrastructure_providers', InfrastructureProviderViewSet, basename="infrastructure_providers")
router.register(r'export_stats', ExportResultStatViewSet, basename="export_stats")
router.register(r'', ExportViewSet, basename="exports")

urlpatterns = [path('', include(router.urls))]
