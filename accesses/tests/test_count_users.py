import datetime

from django.test import TestCase
from django.db import transaction
from django.utils.timezone import now

from accesses.models import Perimeter, Access, Role
from accesses.services.perimeters import count_allowed_users, count_allowed_users_from_above_levels, count_allowed_users_in_inferior_levels
from accesses.tests.base import create_perimeters_hierarchy
from admin_cohort.tests.tests_tools import new_user_and_profile



class CountUsersOnPerimetersBaseTest(TestCase):
    """
    for the tests, we'll be using the perimeters hierarchy defined in the base.py file
    """

    def setUp(self):
        _ = create_perimeters_hierarchy()

        # perimeters on which accesses will be granted
        self.aphp = Perimeter.objects.get(id=9999)
        self.p0 = Perimeter.objects.get(id=0)
        self.p1 = Perimeter.objects.get(id=1)
        self.p2 = Perimeter.objects.get(id=2)
        self.p3 = Perimeter.objects.get(id=3)
        self.p4 = Perimeter.objects.get(id=4)
        self.p5 = Perimeter.objects.get(id=5)
        self.p6 = Perimeter.objects.get(id=6)
        self.p11 = Perimeter.objects.get(id=11)
        self.p12 = Perimeter.objects.get(id=12)

        # create some basic role to assign for all users (doesn't matter)
        self.some_role = Role.objects.create(name='some role', right_read_patient_nominative=True)

        # creates profiles: each one named according to a perimeter
        self.profile_aphp = new_user_and_profile()[1]
        self.profile_p0 = new_user_and_profile()[1]
        self.profile_p1 = new_user_and_profile()[1]
        self.profile_p2 = new_user_and_profile()[1]
        self.profile_p3 = new_user_and_profile()[1]
        self.profile_p5 = new_user_and_profile()[1]
        self.profile_p11 = new_user_and_profile()[1]
        self.profile_p12 = new_user_and_profile()[1]

        # create accesses: one access per profile per perimeter
        defaults = dict(role=self.some_role,
                        start_datetime=now(),
                        end_datetime=now() + datetime.timedelta(days=100)
                        )
        Access.objects.create(perimeter=self.aphp, profile=self.profile_aphp, **defaults)

        Access.objects.create(perimeter=self.p0, profile=self.profile_p0, **defaults)
        Access.objects.create(perimeter=self.p0, profile=self.profile_p1, **defaults)  # second access on perimeter p0

        Access.objects.create(perimeter=self.p1, profile=self.profile_p1, **defaults)

        Access.objects.create(perimeter=self.p2, profile=self.profile_p2, **defaults)
        Access.objects.create(perimeter=self.p2, profile=self.profile_p2, **defaults)  # second access for profile_p2 on perimeter p2

        Access.objects.create(perimeter=self.p3, profile=self.profile_p3, **defaults)
        Access.objects.create(perimeter=self.p5, profile=self.profile_p5, **defaults)
        Access.objects.create(perimeter=self.p11, profile=self.profile_p11, **defaults)
        Access.objects.create(perimeter=self.p12, profile=self.profile_p12, **defaults)

        # create one additional disabled profile
        self.disabled_profile = new_user_and_profile()[1]
        self.disabled_profile.is_active = False
        self.disabled_profile.save()

        # create access for the disabled profile
        Access.objects.create(perimeter=self.p5, profile=self.disabled_profile, **defaults)


class CountAllowedUsersTest(CountUsersOnPerimetersBaseTest):

    def test_user_count_update(self):
        """
        Ensure user counts are correctly updated for perimeters with valid access profiles.
        """
        count_allowed_users()

        self.p0.refresh_from_db()
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()

        self.assertEqual(self.p0.count_allowed_users, 2)
        self.assertEqual(self.p1.count_allowed_users, 1)
        self.assertEqual(self.p2.count_allowed_users, 1)

    def test_no_update_if_count_did_not_change(self):
        """
        Ensure no update is made if the count is already correct.
        """
        self.p12.count_allowed_users = 1
        self.p12.save()

        with transaction.atomic():
            count_allowed_users()

        self.p12.refresh_from_db()
        self.assertEqual(self.p12.count_allowed_users, 1)


class CountAllowedUsersFromAboveLevelsTest(CountUsersOnPerimetersBaseTest):

    def test_user_count_update(self):
        count_allowed_users_from_above_levels()

        self.p0.refresh_from_db()
        self.p6.refresh_from_db()
        self.p11.refresh_from_db()

        self.assertEqual(self.p0.count_allowed_users_above_levels, 1)  # coming from: APHP (1 user)
        self.assertEqual(self.p6.count_allowed_users_above_levels, 2)  # coming from: APHP (1 user), P1 (1 user)
        self.assertEqual(self.p11.count_allowed_users_above_levels, 3)  # coming from: APHP (1 user), P0 (2 users)


class CountAllowedUsersInInferiorLevelsTest(CountUsersOnPerimetersBaseTest):

    def test_user_count_update(self):
        count_allowed_users_in_inferior_levels()

        self.aphp.refresh_from_db()
        self.p0.refresh_from_db()
        self.p4.refresh_from_db()
        self.p11.refresh_from_db()
        self.p12.refresh_from_db()

        self.assertEqual(self.aphp.count_allowed_users_inferior_levels, 7)
        self.assertEqual(self.p0.count_allowed_users_inferior_levels, 4)
        self.assertEqual(self.p4.count_allowed_users_inferior_levels, 2)
        self.assertEqual(self.p11.count_allowed_users_inferior_levels, 0)   # leaf perimeter
        self.assertEqual(self.p12.count_allowed_users_inferior_levels, 0)   # leaf perimeter