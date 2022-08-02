from django.urls import path, include
from rest_framework import routers

from exports.views import ExportRequestViewset, UsersViewSet, CohortViewSet

# class NestedDefaultRouter(NestedRouterMixin, routers.DefaultRouter):
#     pass
#
#
# router = NestedDefaultRouter()

router = routers.DefaultRouter()
router.register(r'unix-accounts', UsersViewSet, basename="unix-accounts")
router.register(r'cohorts', CohortViewSet, basename="cohorts")
router.register(r'', ExportRequestViewset, basename="exports")

urlpatterns = [
    path('', include(router.urls)),
]
