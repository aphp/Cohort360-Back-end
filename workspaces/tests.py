import json

from rest_framework import status
from rest_framework.test import force_authenticate

from admin_cohort.settings import RANGER_HIVE_POLICY_TYPES
from admin_cohort.tests_tools import BaseTests, new_user_and_profile
from admin_cohort.tools import prettify_json
from workspaces.views import RangerHivePolicyViewSet


class RangerHivePolicieTypesTests(BaseTests):
    def setUp(self):
        super(RangerHivePolicieTypesTests, self).setUp()
        self.user_with_no_right, _ = new_user_and_profile(email='with@no.right')

    def test_get_types(self):
        request = self.factory.get(path="/ranger_hive_policies/types")
        force_authenticate(request, self.user_with_no_right)

        response = RangerHivePolicyViewSet.as_view({'get': 'get_types'})(request)
        response.render()

        msg = (prettify_json(response.content) if response.content else "")
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=msg)
        result = json.loads(response.content)

        self.assertTrue(isinstance(result, list), msg)
        self.assertCountEqual(result, RANGER_HIVE_POLICY_TYPES, msg)
