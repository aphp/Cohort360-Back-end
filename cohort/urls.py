from django.urls import include, path

from admin_cohort.urls import NestedDefaultRouter
from cohort.views import RequestViewSet, RequestQuerySnapshotViewSet, CohortResultViewSet, DatedMeasureViewSet, \
    NestedRequestViewSet, NestedRqsViewSet, FolderViewSet
from cohort.views.fhir_filter import FhirFilterViewSet

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

router.register(r'dated-measures', DatedMeasureViewSet, basename="dated-measures")
router.register(r'cohorts', CohortResultViewSet, basename="cohort-results")
router.register(r'fhir-filters', FhirFilterViewSet, basename="fhir-filter")

urlpatterns = [path('', include(router.urls))]
