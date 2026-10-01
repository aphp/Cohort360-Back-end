from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from accesses.models import Perimeter, Role
from admin_cohort.management.commands import load_initial_data, reset_onboarding
from admin_cohort.models import User
from admin_cohort.tests.tests_tools import TestCaseWithDBs


class LoadInitialDataCommandTest(TestCaseWithDBs):
    def test_load_initial_data_command(self):
        out = StringIO()
        file_path = "admin_cohort/tests/perimeters.example.csv"
        call_command(load_initial_data.Command(), perimeters_conf=file_path, stdout=out)
        perimeters = Perimeter.objects.all()
        user = User.objects.filter(username__icontains="admin")
        admin_role = Role.objects.filter(right_full_admin=True)
        self.assertIsNotNone(perimeters)
        self.assertIsNotNone(user)
        self.assertIsNotNone(admin_role)
        self.assertIn("Successfully added user", out.getvalue())


class ResetOnboardingCommandTest(TestCaseWithDBs):
    def setUp(self):
        now = timezone.now()
        self.old_update = now - timedelta(days=30)
        self.onboarded = User.objects.create(username="1111111", email="user01@aphp.fr")
        self.in_progress = User.objects.create(username="2222222", email="user02@aphp.fr")
        self.not_started = User.objects.create(username="3333333", email="user03@aphp.fr")
        self.deleted = User.objects.create(username="4444444", email="user04@aphp.fr")
        User.objects.filter(username__in=["1111111", "4444444"]).update(
            onboarding_step=User.ONBOARDING_TOTAL_STEPS, onboarding_completed_at=now, charter_signed_at=now
        )
        User.objects.filter(username="2222222").update(onboarding_step=1)
        User.objects.all().update(update_datetime=self.old_update)
        User.objects.filter(username="4444444").update(delete_datetime=now)

    def call(self, *args):
        out = StringIO()
        with mock.patch.object(reset_onboarding, "invalidate_cache") as invalidate_cache:
            call_command(reset_onboarding.Command(), *args, stdout=out)
        return out.getvalue(), invalidate_cache

    def get_user(self, username):
        return User.objects.all(even_deleted=True).get(username=username)

    def assert_reset(self, username):
        user = self.get_user(username)
        self.assertEqual(user.onboarding_step, 0)
        self.assertIsNone(user.onboarding_completed_at)
        self.assertIsNone(user.charter_signed_at)
        self.assertGreater(user.update_datetime, self.old_update)

    def assert_untouched(self, username):
        user = self.get_user(username)
        self.assertEqual(user.update_datetime, self.old_update)

    def test_requires_a_target(self):
        with self.assertRaises(CommandError):
            self.call()

    def test_all_resets_every_started_onboarding(self):
        output, invalidate_cache = self.call("--all")
        self.assertIn("Onboarding réinitialisé pour 2 utilisateur(s).", output)
        self.assert_reset("1111111")
        self.assert_reset("2222222")
        self.assert_untouched("3333333")
        invalidate_cache.assert_called_once_with(model_name="User")

    def test_all_skips_deleted_users(self):
        self.call("--all")
        deleted = self.get_user("4444444")
        self.assertEqual(deleted.onboarding_step, User.ONBOARDING_TOTAL_STEPS)
        self.assertIsNotNone(deleted.onboarding_completed_at)
        self.assertIsNotNone(deleted.charter_signed_at)
        self.assert_untouched("4444444")

    def test_usernames_resets_only_targeted_users(self):
        output, invalidate_cache = self.call("--usernames", "1111111")
        self.assertIn("Onboarding réinitialisé pour 1 utilisateur(s).", output)
        self.assert_reset("1111111")
        self.assertEqual(self.get_user("2222222").onboarding_step, 1)
        self.assert_untouched("2222222")
        invalidate_cache.assert_called_once_with(model_name="User")

    def test_usernames_fails_on_unknown_user(self):
        with self.assertRaisesMessage(CommandError, "Utilisateurs introuvables : inconnu"):
            self.call("--usernames", "1111111", "inconnu")
        self.assertEqual(self.get_user("1111111").onboarding_step, User.ONBOARDING_TOTAL_STEPS)
        self.assert_untouched("1111111")

    def test_usernames_fails_on_deleted_user(self):
        with self.assertRaisesMessage(CommandError, "Utilisateurs introuvables : 4444444"):
            self.call("--usernames", "4444444")

    def test_dry_run_counts_without_writing(self):
        output, invalidate_cache = self.call("--all", "--dry-run")
        self.assertIn("2 utilisateur(s) à réinitialiser.", output)
        self.assertEqual(self.get_user("1111111").onboarding_step, User.ONBOARDING_TOTAL_STEPS)
        self.assertEqual(self.get_user("2222222").onboarding_step, 1)
        self.assert_untouched("1111111")
        self.assert_untouched("2222222")
        invalidate_cache.assert_not_called()

    def test_dry_run_with_usernames_counts_targeted_users(self):
        output, _ = self.call("--usernames", "2222222", "3333333", "--dry-run")
        self.assertIn("1 utilisateur(s) à réinitialiser.", output)
