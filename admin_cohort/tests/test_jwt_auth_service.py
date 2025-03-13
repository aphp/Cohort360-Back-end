from unittest.mock import patch, MagicMock
from django.test import TestCase
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