import hashlib
from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed

from admin_cohort.exceptions import NoIdentityServerConfigured
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

    @patch.object(JWTAuth, attribute="check_credentials_against_server")
    def test_jwt_auth_check_credentials_locally(self, mock_check_against_server):
        mock_check_against_server.side_effect = NoIdentityServerConfigured()
        self.assertTrue(self.jwt_auth.check_credentials(username=self.test_user.username,
                                                        password=self.test_password))
        mock_check_against_server.assert_called()

    @patch("admin_cohort.services.auth.IDENTITY_SERVER_AUTH_ENDPOINT", "/auth/login")
    def test_jwt_auth_check_credentials_against_server(self):
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