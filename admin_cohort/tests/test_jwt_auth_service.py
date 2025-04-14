import jwt
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.test import TestCase

from accesses.models import Perimeter, Role, Access, Profile
from admin_cohort.models import User
from admin_cohort.services.auth import JWTAuth


class JWTAuthTestCase(TestCase):

    def setUp(self):
        self.jwt_auth = JWTAuth()

    def test_jwt_auth_authenticate(self):
        with patch.object(JWTAuth, "decode_token", return_value={"username": "test_user"}):
            username = self.jwt_auth.authenticate(token="some_token")
            self.assertEqual(username, "test_user")

    def test_jwt_auth_check_credentials_success(self):
        with patch(target="requests.post", return_value=MagicMock(status_code=200)) as mock_post:
            self.assertTrue(self.jwt_auth.check_credentials("user", "pass"))
            mock_post.assert_called()

    def test_jwt_auth_check_credentials_failure(self):
        with patch(target="requests.post", return_value=MagicMock(status_code=401)):
            self.assertFalse(self.jwt_auth.check_credentials("user", "pass"))

    def test_jwt_auth_login(self):
        mock_request = MagicMock()
        mock_request.data = {"username": "test_user", "password": "password"}
        with patch(target="admin_cohort.services.auth.TokenObtainPairSerializer") as mock_serializer:
            mock_instance = mock_serializer.return_value
            mock_instance.is_valid.return_value = True
            mock_instance.user = "mock_user"
            mock_instance.validated_data = {"access": "token", "refresh": "refresh_token"}
            user = self.jwt_auth.login(mock_request)
            self.assertEqual(user, "mock_user")

    def test_jwt_auth_refresh_token(self):
        with patch(target="admin_cohort.services.auth.TokenRefreshSerializer") as mock_serializer:
            mock_instance = mock_serializer.return_value
            mock_instance.is_valid.return_value = True
            mock_instance.validated_data = {"access": "new_token", "refresh": "new_refresh_token"}
            tokens = self.jwt_auth.refresh_token("refresh_token")
            self.assertEqual(tokens.access_token, "new_token")

    def test_generate_system_token_creates_user_and_returns_token(self):
        """Test that generate_system_token creates a system user and returns tokens."""
        # Ensure user does not exist before function call
        self.assertFalse(User.objects.filter(username="system").exists())

        # Mock Perimeter and Role
        root_perimeter = Perimeter.objects.create(name="Root Perimeter", pk=settings.ROOT_PERIMETER_ID)
        admin_role = Role.objects.create(name="Admin", right_full_admin=True)

        token = self.jwt_auth.generate_system_token()

        system_user = User.objects.filter(username="system").first()
        self.assertIsNotNone(system_user)

        profile = Profile.objects.get(user=system_user)
        self.assertTrue(profile.is_active)

        accesses = Access.objects.filter(profile=profile)
        self.assertTrue(accesses.count() == 1)
        access = accesses.first()
        self.assertEqual(access.perimeter, root_perimeter)
        self.assertEqual(access.role, admin_role)
        self.assertIsInstance(token, str)
        decoded = jwt.decode(jwt=token, options={'verify_signature': False})
        self.assertEqual(decoded["username"], "system")


    def test_generate_system_token_uses_existing_user(self):
        """Test that generate_system_token for an existing system user."""
        _ = User.objects.create(username="system",
                                firstname="System",
                                lastname="System",
                                email="system.dj@system.com")
        token = self.jwt_auth.generate_system_token()
        self.assertEqual(User.objects.filter(username="system").count(), 1)
        self.assertIsInstance(token, str)
        decoded = jwt.decode(jwt=token, options={'verify_signature': False})
        self.assertEqual(decoded["username"], "system")

    @patch("admin_cohort.services.auth.TokenObtainPairSerializer.get_token")
    def test_generate_system_token_handles_token_error(self, mock_get_token):
        """Test that generate_system_token handles token generation errors."""
        mock_get_token.side_effect = Exception("Token error")
        with self.assertRaises(Exception):
            self.jwt_auth.generate_system_token()
