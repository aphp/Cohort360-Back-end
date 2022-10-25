from django.urls import path, include
from rest_framework import routers

from exports.views import ExportRequestViewset, UnixAccountViewSet, CohortViewSet


router = routers.DefaultRouter()
router.register(r'', ExportRequestViewset, basename="exports")
router.register(r'unix-accounts', UnixAccountViewSet, basename="unix-accounts")
router.register(r'cohorts', CohortViewSet, basename="cohorts")

urlpatterns = [path('', include(router.urls))]
