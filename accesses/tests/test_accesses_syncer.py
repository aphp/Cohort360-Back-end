from datetime import timedelta

from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock

from accesses.models import Profile, Access, Role, Perimeter
from accesses.services.accesses_syncer import AccessesSynchronizer
from admin_cohort.models import User

MANUAL, ORBIS = settings.ACCESS_SOURCES


class AccessesSynchronizerTests(TestCase):

    def setUp(self):
        super().setUp()
        self.token = "some-secret-token"
        self.test_user = User.objects.create(username="test_user", firstname="Test", lastname="TEST", email="test@test.fr")
        Profile.objects.create(user=self.test_user, is_active=True, source=MANUAL)

        with patch("accesses.services.accesses_syncer.jwt_auth_service.generate_system_token", return_value=self.token):
            with patch("accesses.services.accesses_syncer.SyncFHIRClient"):
                self.syncer = AccessesSynchronizer()

    def test_sync_profiles_creates_profiles(self):
        """Test that sync_profiles creates ORBIS-type profile for active practitioners."""
        mock_practitioner = MagicMock()
        mock_practitioner.active = True
        mock_practitioner.identifier = [MagicMock(value="test_user")]
        mock_practitioner.name = [MagicMock(given=["Test"], family="TEST")]
        self.syncer.fhir_client.resources.return_value.fetch_all.return_value = [mock_practitioner]
        self.syncer.sync_profiles()
        self.assertTrue(Profile.objects.filter(user=self.test_user, source=ORBIS, is_active=True).exists())

    def test_sync_profiles_deactivates_profiles_and_accesses_for_inactive_practitioners(self):
        """Test that sync_profiles creates ORBIS-type profile for active practitioners."""
        orbis_profile = Profile.objects.create(user=self.test_user, is_active=True, source=ORBIS)
        role = Role.objects.create(name="Sample Role")
        perimeter = Perimeter.objects.create(id=1, name="P1", local_id="p1")
        Access.objects.create(profile=orbis_profile,
                              role=role,
                              perimeter=perimeter,
                              start_datetime=timezone.now(),
                              end_datetime=timezone.now() + timedelta(days=10))

        mock_practitioner = MagicMock()
        mock_practitioner.active = False
        mock_practitioner.identifier = [MagicMock(value="test_user")]

        self.syncer.fhir_client.resources.return_value.fetch_all.return_value = [mock_practitioner]
        self.syncer.sync_profiles()
        for p in Profile.objects.filter(user=self.test_user, source=ORBIS):
            self.assertFalse(p.is_active)
        for access in orbis_profile.accesses.all():
            self.assertFalse(access.is_valid)

    @patch.object(AccessesSynchronizer, attribute="get_mapped_role")
    @patch.object(AccessesSynchronizer, attribute="send_report_notification")
    def test_sync_accesses_creates_accesses(self, mock_mapped_role, mock_report_notif):
        """Test that sync_accesses creates new accesses when required."""
        mock_report_notif.return_value = None
        mock_mapped_role.return_value = Role.objects.create(name="Some ORBIS Role")
        Perimeter.objects.create(id=2, name="P1", local_id="p1")

        mock_practitioner_role = MagicMock()
        mock_practitioner_role.resource_type = "PractitionerRole"
        mock_practitioner_role.active = True
        mock_practitioner_role.id = 1234
        mock_practitioner_role.practitioner.to_resource.return_value = MagicMock(identifier=[MagicMock(value="test_user")])
        mock_practitioner_role.organization.id = 2
        mock_practitioner_role.code = [MagicMock(coding=[MagicMock(code="admin_role")])]
        mock_practitioner_role.period = MagicMock(start=timezone.now(), end=timezone.now() + timedelta(days=10))

        self.syncer.fhir_client.resources.return_value.\
            revinclude.return_value.\
            search.return_value.\
            fetch_raw.return_value = MagicMock(entry=[MagicMock(resource=mock_practitioner_role)])
        self.syncer.sync_accesses()
        mock_report_notif.assert_called_once()

    @patch("accesses.services.accesses_syncer.EmailNotification.push")
    @patch("accesses.services.accesses_syncer.EmailNotification.attach_logo")
    @patch("accesses.services.accesses_syncer.settings")
    def test_send_report_notification_sends_email(self, mock_settings, mock_attach_logo, mock_email_push):
        """Test that send_report_notification correctly sends an email notification."""
        mock_settings.ADMINS = [("Admin", "admin-email@test.fr")]
        mock_attach_logo.return_value = None
        count_orbis_accesses = 1
        count_new_accesses = 1
        skipped_roles = ["role1", "role2"]
        missing_perimeters = [1, 2]

        AccessesSynchronizer.send_report_notification(skipped_roles, missing_perimeters, count_orbis_accesses, count_new_accesses)
        mock_email_push.assert_called_once()
