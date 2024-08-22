from django.urls import path, include
from rest_framework.routers import SimpleRouter

from accesses_fhir_perimeters.views import FhirPerimeterResult

router = SimpleRouter()

router.register(r'', FhirPerimeterResult, basename="fhir-perimeter-results")
urlpatterns = [path('', include(router.urls))]
