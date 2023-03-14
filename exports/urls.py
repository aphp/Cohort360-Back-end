from django.urls import path, include
from rest_framework.routers import DefaultRouter

from exports.views import ExportRequestViewSet, CohortViewSet
from exports.views.unix_account import UnixAccountViewSet

router = DefaultRouter()
router.register(r'unix-accounts', UnixAccountViewSet, basename="unix-accounts")
router.register(r'cohorts', CohortViewSet, basename="cohorts")
router.register(r'', ExportRequestViewSet, basename="exports")

urlpatterns = [path('', include(router.urls))]
