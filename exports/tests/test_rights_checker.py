from rest_framework.exceptions import ValidationError

from cohort.models import CohortResult, RequestQuerySnapshot
from exports.services.rights_checker import rights_checker
from exports.tests.base_test import ExportsTestBase


class RightsCheckerTestCase(ExportsTestBase):
    def test_cohort_without_perimeter_in_snapshot_is_rejected(self):
        rqs = RequestQuerySnapshot.objects.create(owner=self.exporter_user, request=self.request, serialized_query="{}", perimeters_ids=None)
        cohort = CohortResult.objects.create(owner=self.exporter_user, request_query_snapshot=rqs)
        with self.assertRaises(ValidationError):
            rights_checker.check_owner_rights(owner=self.user_without_rights, output_format="csv", nominative=False, source_cohorts_ids=[cohort.pk])

    def test_cohort_without_snapshot_is_rejected(self):
        cohort = CohortResult.objects.create(owner=self.exporter_user, request_query_snapshot=None)
        with self.assertRaises(ValidationError):
            rights_checker.check_owner_rights(owner=self.user_without_rights, output_format="csv", nominative=False, source_cohorts_ids=[cohort.pk])
