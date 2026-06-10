from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.test import TestCase, override_settings
from django.utils import timezone

from accesses.accesses_alerts import send_access_expiry_alerts
from accesses.models import Access, Profile, Role, Perimeter
from admin_cohort.models import User


class AccessExpiryAlertsDisabledTests(TestCase):
    """
    Tests for the ENABLE_ACCESS_EXPIRY_ALERTS setting.

    Bug context (Issue #3103):
    After prod<->preprod deployment swaps, preprod was also running the scheduled
    task and sending alert emails from its database (formerly prod).

    Fix: Added ENABLE_ACCESS_EXPIRY_ALERTS env var (True in prod only, False elsewhere).
    """

    def setUp(self):
        super().setUp()
        self.role = Role.objects.create(name="Test Role")
        self.perimeter = Perimeter.objects.create(id=1, name="P1", local_id="p1")

    def _create_user_with_profile(self, username: str) -> tuple[User, Profile]:
        user = User.objects.create(username=username, firstname="Test", lastname="USER", email=f"{username}@test.fr")
        profile = Profile.objects.create(user=user, is_active=True, source=settings.ACCESS_SOURCES[0])
        return user, profile

    @patch("accesses.accesses_alerts.send_alert_email")
    def test_no_alerts_when_disabled_by_default(self, mock_send_alert_email: MagicMock):
        """
        Test that NO alerts are sent when ENABLE_ACCESS_EXPIRY_ALERTS=False (default).

        This is the main fix for Issue #3103: after prod<->preprod swaps, preprod
        was also running the scheduled task and sending alert emails. By setting
        ENABLE_ACCESS_EXPIRY_ALERTS=False in non-prod environments, we prevent this.
        """
        days = 30
        expiry_datetime = timezone.now() + timedelta(days=days)

        # Create user with expiring access that would normally trigger an alert
        user, profile = self._create_user_with_profile("user_disabled_test")
        Access.objects.create(
            profile=profile,
            role=self.role,
            perimeter=self.perimeter,
            start_datetime=timezone.now() - timedelta(days=10),
            end_datetime=expiry_datetime,
        )

        # With ENABLE_ACCESS_EXPIRY_ALERTS=False (default), no alert should be sent
        send_access_expiry_alerts(days=days)

        mock_send_alert_email.assert_not_called()

    @override_settings(ENABLE_ACCESS_EXPIRY_ALERTS=True)
    @patch("accesses.accesses_alerts.send_alert_email")
    def test_alerts_sent_when_enabled(self, mock_send_alert_email: MagicMock):
        """Test that alerts ARE sent when ENABLE_ACCESS_EXPIRY_ALERTS=True."""
        days = 30
        expiry_datetime = timezone.now() + timedelta(days=days)

        user, profile = self._create_user_with_profile("user_enabled_test")
        Access.objects.create(
            profile=profile,
            role=self.role,
            perimeter=self.perimeter,
            start_datetime=timezone.now() - timedelta(days=10),
            end_datetime=expiry_datetime,
        )

        send_access_expiry_alerts(days=days)

        mock_send_alert_email.assert_called_once()
        call_args = mock_send_alert_email.call_args
        self.assertEqual(call_args.kwargs["user"], user)
        self.assertEqual(call_args.kwargs["days"], days)

    @override_settings(ENABLE_ACCESS_EXPIRY_ALERTS=True)
    @patch("accesses.accesses_alerts.send_alert_email")
    def test_no_alert_when_access_not_expiring_on_target_date(self, mock_send_alert_email: MagicMock):
        """Test that no alert is sent when user's access expires on a different date."""
        days = 30

        # Create user with access expiring in 60 days (not on target date)
        user, profile = self._create_user_with_profile("user_different_date")
        Access.objects.create(
            profile=profile,
            role=self.role,
            perimeter=self.perimeter,
            start_datetime=timezone.now() - timedelta(days=10),
            end_datetime=timezone.now() + timedelta(days=60),
        )

        send_access_expiry_alerts(days=days)

        mock_send_alert_email.assert_not_called()
