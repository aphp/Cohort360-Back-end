from rest_framework.exceptions import PermissionDenied

from accesses.utils import impersonate_hook
from accesses.tests.base import AccessesAppTestsBase


class TestImpersonateHook(AccessesAppTestsBase):

    def test_no_impersonating(self):
        impersonated = impersonate_hook(self.user_y, {})
        assert impersonated == self.user_y

    def test_impersonating_success(self):
        self.create_new_access_for_user(profile=self.profile_y, role=self.role_full_admin, perimeter=self.aphp)
        impersonated = impersonate_hook(self.user_y, {"X-Impersonate": self.user_z.username})
        assert impersonated == self.user_z

    def test_impersonating_failed_no_rights(self):
        with self.assertRaises(PermissionDenied):
            impersonate_hook(self.user_t, {"X-Impersonate": self.user_z.username})

    def test_impersonating_failed_no_existing_user(self):
        self.create_new_access_for_user(profile=self.profile_y, role=self.role_full_admin, perimeter=self.aphp)
        impersonated = impersonate_hook(self.user_y, {"X-Impersonate": "foo"})
        assert impersonated == self.user_y
