from django.urls import include, path
from rest_framework import routers
from rest_framework_extensions.routers import NestedRouterMixin

from cohort.views import RequestViewSet, RequestQuerySnapshotViewSet, CohortResultViewSet, DatedMeasureViewSet, \
    NestedRequestViewSet, NestedRqsViewSet, NestedDatedMeasureViewSet, \
    NestedCohortResultViewSet, FolderViewSet


class NestedDefaultRouter(NestedRouterMixin, routers.DefaultRouter):
    pass


router = NestedDefaultRouter()

folder_router = router.register(r'folders', FolderViewSet, basename="folders")
folder_router.register('requests', NestedRequestViewSet, basename="folder-requests",
                       parents_query_lookups=["parent_folder"])

req_router = router.register(r'requests', RequestViewSet, basename="requests")
req_router.register('query-snapshots', NestedRqsViewSet, basename="request-request-query-snapshots",
                    parents_query_lookups=["request_id"])

rqs_router = router.register(r'request-query-snapshots', RequestQuerySnapshotViewSet)
rqs_router.register('next-snapshots', NestedRqsViewSet, basename="request-query-snapshot-next-snapshots",
                    parents_query_lookups=["previous_snapshot"])
rqs_router.register('dated-measures', NestedDatedMeasureViewSet, basename="request-query-snapshot-dated-measures",
                    parents_query_lookups=["request_query_snapshot"])
rqs_router.register('cohorts', NestedCohortResultViewSet, basename="request-query-snapshot-cohort-results",
                    parents_query_lookups=["request_query_snapshot"])

router.register(r'dated-measures', DatedMeasureViewSet, basename="dated-measures")
router.register(r'cohorts', CohortResultViewSet, basename="cohort-results")

urlpatterns = [path('', include(router.urls))]
