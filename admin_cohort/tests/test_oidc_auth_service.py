import jwt
from unittest.mock import patch, MagicMock
from django.test import TestCase
from admin_cohort.services.auth import OIDCAuth, OIDCAuthConfig, get_issuer_certs, build_oidc_configs
from requests.exceptions import RequestException


class OIDCAuthTestCase(TestCase):

    def setUp(self):
        self.oidc_config = OIDCAuthConfig(
            issuer="https://example.com",
            client_id="client123",
            client_secret="secret123",
            grant_type="authorization_code",
            redirect_uri="https://app.com/callback"
        )
        with patch(target="admin_cohort.services.auth.env", side_effect=lambda key, default=None: default):
            self.oidc_auth = OIDCAuth()
            self.oidc_auth.oidc_configs = [self.oidc_config]

    def test_oidc_auth_init(self):
        self.assertIsInstance(self.oidc_auth, OIDCAuth)
        self.assertEqual(self.oidc_auth.USERNAME_LOOKUP, "preferred_username")

    def test_oidc_auth_get_oidc_config(self):
        self.oidc_auth.oidc_configs = [self.oidc_config]
        self.assertEqual(self.oidc_auth.get_oidc_config(client_id="client123"), self.oidc_config)

    def test_oidc_auth_decode_token(self):
        token = jwt.encode({"iss": "https://example.com"}, "secret", algorithm="HS256")
        with patch(target="jwt.decode", return_value={"iss": "https://example.com"}):
            decoded = self.oidc_auth.decode_token(token, verify_signature=False)
            self.assertEqual(decoded["iss"], "https://example.com")

    def test_oidc_authenticate(self):
        token = jwt.encode({"iss": "https://example.com", "kid": "test_kid"}, "secret", algorithm="HS256")
        with patch(target="admin_cohort.services.auth.get_issuer_certs", return_value={"test_kid": "public_key"}):
            with patch.object(target=OIDCAuth, attribute="decode_token", return_value={"iss": self.oidc_config.issuer,
                                                                                       "preferred_username": "test_user"}):
                with patch(target="admin_cohort.services.auth.jwt.get_unverified_header", return_value={"kid": "test_kid"}):
                    username = self.oidc_auth.authenticate(token)
                    self.assertEqual(username, "test_user")

    def test_build_oidc_configs(self):
        with patch(target="admin_cohort.services.auth.env",
                   side_effect=lambda key, default=None: "https://example.com" if "OIDC_AUTH_SERVER_1" in key else default):
            configs = build_oidc_configs()
            self.assertEqual(len(configs), 1)
            self.assertEqual(configs[0].issuer, "https://example.com")

    def test_get_issuer_certs(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"keys": [{"kid": "test_kid", "kty": "RSA", "n": "nnnn", "e": "eee"}]}

        with patch(target="requests.get", return_value=mock_response):
            certs = get_issuer_certs("https://example.com")
            self.assertIn("test_kid", certs)

    def test_oidc_auth_logout(self):
        with patch.object(target=OIDCAuth, attribute="decode_token", return_value={"azp": self.oidc_config.client_id}):
            with patch.object(target=OIDCAuth, attribute="get_oidc_config", return_value=self.oidc_config):
                with patch(target="requests.post", return_value=MagicMock(status_code=204)) as mock_post:
                    self.oidc_auth.logout({"refresh_token": "test_refresh"}, "access_token")
                    mock_post.assert_called()

    def test_oidc_auth_logout_fail(self):
        with patch.object(target=OIDCAuth, attribute="decode_token", return_value={"azp": self.oidc_config.client_id}):
            with patch.object(target=OIDCAuth, attribute="get_oidc_config", return_value=self.oidc_config):
                with patch(target="requests.post", return_value=MagicMock(status_code=400, text="Error")):
                    with self.assertRaises(RequestException):
                        self.oidc_auth.logout({"refresh_token": "test_refresh"}, "access_token")

    def test_get_tokens_success(self):
        with patch("requests.post", return_value=MagicMock(status_code=200, json=lambda: {"access_token": "test_access",
                                                                                          "refresh_token": "test_refresh"})) as mock_post:
            tokens = self.oidc_auth.get_tokens(code="test_code", redirect_uri="https://app.com/callback")
            self.assertIsNotNone(tokens)
            self.assertEqual(tokens.access_token, "test_access")
            self.assertEqual(tokens.refresh_token, "test_refresh")
            mock_post.assert_called()

    def test_get_tokens_failure(self):
        with patch("requests.post", return_value=MagicMock(status_code=400, text="Error")):
            tokens = self.oidc_auth.get_tokens(code="test_code", redirect_uri="https://app.com/callback")
            self.assertIsNone(tokens)

    def test_refresh_token_success(self):
        with patch.object(OIDCAuth, "decode_token", return_value={"azp": "client123"}):
            with patch("requests.post", return_value=MagicMock(status_code=200, json=lambda: {"access_token": "new_access",
                                                                                              "refresh_token": "new_refresh"})) as mock_post:
                tokens = self.oidc_auth.refresh_token(token="old_refresh_token")
                self.assertIsNotNone(tokens)
                self.assertEqual(tokens.access_token, "new_access")
                self.assertEqual(tokens.refresh_token, "new_refresh")
                mock_post.assert_called()

    def test_refresh_token_failure(self):
        with patch.object(OIDCAuth, "decode_token", return_value={"azp": "client123"}):
            with patch("requests.post", return_value=MagicMock(status_code=400, text="Error")):
                with self.assertRaises(Exception):
                    self.oidc_auth.refresh_token(token="old_refresh_token")

    def test_retrieve_username(self):
        with patch.object(OIDCAuth, "decode_token", return_value={"preferred_username": "test_user"}):
            username = self.oidc_auth.retrieve_username(token="some_token")
            self.assertEqual(username, "test_user")
