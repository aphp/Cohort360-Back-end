from datetime import timedelta

from django.utils import timezone

from accesses.models import Role, Access
from accesses.services.accesses import accesses_service
from accesses.tests.base import AccessesAppTestsBase
from admin_cohort.tests.tests_tools import new_user_and_profile


class CanUserManageAccessTests(AccessesAppTestsBase):
    def test_role_with_only_the_right_to_extract_export_purposes_requires_managing_data_accesses_on_the_perimeter(self):
        # The extraction lists the exports of all users: the role must not be assignable by any accesses manager on any perimeter
        role_purposes_extractor = Role.objects.create(name="PURPOSES EXTRACTOR", right_extract_export_purposes=True)
        user_admin_accesses_manager_on_p1, profile = new_user_and_profile()
        Access.objects.create(
            profile=profile,
            role=self.role_admin_accesses_manager,
            perimeter=self.p1,
            start_datetime=timezone.now(),
            end_datetime=timezone.now() + timedelta(days=365),
        )
        for perimeter, can_manage in ((self.p1, True), (self.p0, False)):
            target_access = {"role": role_purposes_extractor, "perimeter": perimeter}
            self.assertEqual(accesses_service.can_user_manage_access(user=user_admin_accesses_manager_on_p1, target_access=target_access), can_manage)
