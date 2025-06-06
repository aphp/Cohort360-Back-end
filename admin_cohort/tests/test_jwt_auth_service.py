import hashlib
import jwt
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.test import TestCase
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed

from admin_cohort.exceptions import NoAuthenticationHookDefined

from accesses.models import Perimeter, Role, Access, Profile
from admin_cohort.models import User
from admin_cohort.services.auth import JWTAuth


class JWTAuthTestCase(TestCase):

    def setUp(self):
        self.jwt_auth = JWTAuth()
        self.test_password = "1234"
        self.test_user = User.objects.create(username='test_user',
                                             email='test.user@backend.fr',
                                             firstname='Test',
                                             lastname='User',
                                             password=hashlib.sha256(self.test_password.encode("utf-8")).hexdigest())

    def test_jwt_auth_authenticate(self):
        with patch.object(JWTAuth, "decode_token", return_value={"username": "test_user"}):
            username = self.jwt_auth.authenticate(token="some_token")
            self.assertEqual(username, "test_user")

    @patch.object(JWTAuth, attribute="authenticate_with_external_services")
    def test_jwt_auth_check_credentials_locally(self, mock_check_against_server):
        mock_check_against_server.side_effect = NoAuthenticationHookDefined()
        self.assertTrue(self.jwt_auth.check_credentials(username=self.test_user.username,
                                                        password=self.test_password))
        mock_check_against_server.assert_called()

    def test_jwt_authenticate_with_external_services(self):
        with patch(target="requests.post", return_value=MagicMock(status_code=status.HTTP_200_OK)):
            res = self.jwt_auth.check_credentials(username=self.test_user.username,
                                                  password=self.test_password)
            self.assertTrue(res)

    def test_jwt_auth_check_credentials_wrong_password(self):
        res = self.jwt_auth.check_credentials(username=self.test_user.username,
                                              password="wrong-password")
        self.assertFalse(res)

    def test_jwt_auth_check_credentials_user_not_found(self):
        with self.assertRaises(AuthenticationFailed):
            self.jwt_auth.check_credentials(username="wrong-username",
                                            password=self.test_password)

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
