import inspect
import json
import logging
from abc import ABC, abstractmethod
from typing import Union, Tuple, Optional, Callable, Dict, List

import environ
import jwt
import requests
from django.conf import settings
from django.contrib.auth import logout
from jwt import InvalidTokenError
from jwt.algorithms import RSAAlgorithm
from requests import RequestException
from rest_framework import status, HTTP_HEADER_ENCODING
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import AUTH_HEADER_TYPE_BYTES
from rest_framework_simplejwt.exceptions import InvalidToken

from admin_cohort.models import User
from admin_cohort.types import ServerError, LoginError, OIDCAuthTokens, JWTAuthTokens, AuthTokens

env = environ.Env()
_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')


class Auth(ABC):
    USERNAME_LOOKUP = None
    tokens_class = None

    def __init__(self):
        assert self.USERNAME_LOOKUP is not None, "`USERNAME_LOOKUP` attribute is not defined"
        assert self.tokens_class is not None, "`tokens_class` attribute is not defined"
        self.algorithms = env("JWT_ALGORITHMS")

    def get_tokens(self, **kwargs) -> AuthTokens:
        response = requests.post(**kwargs)
        if response.status_code == status.HTTP_200_OK:
            return self.tokens_class(**response.json())
        if response.status_code == status.HTTP_401_UNAUTHORIZED:
            raise LoginError("Invalid username or password")
        else:
            raise ServerError(f"Error {response.status_code} from authentication server: {response.text}")

    def refresh_token(self, **kwargs) -> dict:
        response = requests.post(**kwargs)
        if response.status_code == status.HTTP_200_OK:
            return self.tokens_class(**response.json()).__dict__
        elif response.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED):
            raise InvalidToken("Token is invalid or has expired")
        else:
            response.raise_for_status()

    @abstractmethod
    def logout_user(self, *args):
        raise NotImplementedError

    def decode_token(self, token: str, verify_signature=True, key="", issuer=None, audience=None, leeway=0):
        options = {'verify_signature': verify_signature}
        kwargs = {'algorithms': self.algorithms,
                  'key': key,
                  'issuer': issuer,
                  'audience': audience,
                  'leeway': leeway}
        try:
            return jwt.decode(jwt=token, options=options, **kwargs)
        except jwt.PyJWTError as e:
            _logger.info(f"Error decoding token: {e} - `{token}`")
            raise e

    def retrieve_username(self, token_payload: dict) -> str:
        return token_payload.get(self.USERNAME_LOOKUP)


class OIDCAuth(Auth):
    USERNAME_LOOKUP = "preferred_username"
    tokens_class = OIDCAuthTokens

    def __init__(self):
        super().__init__()
        self.oidc_extra_allowed_servers = env("OIDC_EXTRA_SERVER_URLS", default="").split(",")
        self.grant_type = env("OIDC_GRANT_TYPE")
        self.refresh_grant_type = "refresh_token"
        self.oidc_auth_servers = env("OIDC_AUTH_SERVERS").split(";")
        self.audience = env("OIDC_CLIENT_AUDIENCES").split(';')
        self.redirect_uris = env("OIDC_REDIRECT_URIS").split(";")
        self.oidc_configs = {
            oidc_auth_server: {"client_id": env("OIDC_CLIENT_IDS").split(";")[i],
                               "client_secret": env("OIDC_CLIENT_SECRETS").split(";")[i],
                               "oidc_auth_server": self.oidc_auth_servers[i],
                               "audiences": self.audience[i].split(","),
                               "redirect_uri": self.redirect_uris[i]
                               }
            for i, oidc_auth_server in enumerate(self.oidc_auth_servers)
        }

    def get_issuer_from_redirect_uri(self, redirect_uri: str) -> Optional[str]:
        for issuer, config in self.oidc_configs.items():
            if config["redirect_uri"] == redirect_uri:
                return issuer
        raise ValueError(f"Unrecognised redirect_uri: `{redirect_uri}`")

    def get_oidc_config(self, issuer: Optional[str] = None):
        return self.oidc_configs[issuer or self.oidc_auth_servers[0]]

    def client_identity(self, issuer: Optional[str] = None):
        oidc_config = self.get_oidc_config(issuer)
        return {"client_id": oidc_config["client_id"],
                "client_secret": oidc_config["client_secret"]
                }

    @property
    def recognised_issuers(self):
        return self.oidc_auth_servers + self.oidc_extra_allowed_servers

    def get_oidc_url(self, issuer: Optional[str] = None):
        oidc_config = self.get_oidc_config(issuer)
        return f"{oidc_config['oidc_auth_server']}/protocol/openid-connect"

    def token_url(self, issuer: Optional[str] = None):
        return f"{self.get_oidc_url(issuer)}/token"

    def logout_url(self, issuer: Optional[str] = None):
        return f"{self.get_oidc_url(issuer)}/logout"

    def get_tokens(self, code: str, redirect_uri: Optional[str] = None) -> AuthTokens:
        the_redirect_uri = redirect_uri or self.redirect_uris[0]
        issuer = self.get_issuer_from_redirect_uri(the_redirect_uri)
        data = {**self.client_identity(issuer),
                "redirect_uri": the_redirect_uri,
                "grant_type": self.grant_type,
                "code": code
                }
        return super().get_tokens(url=self.token_url(issuer), data=data)

    def refresh_token(self, token: str):
        issuer = self.decode_token(token=token, verify_signature=False).get("iss")
        data = {**self.client_identity(issuer),
                "grant_type": self.refresh_grant_type,
                "refresh_token": token}
        return super().refresh_token(url=self.token_url(issuer), data=data)

    def authenticate(self, token: str) -> str:
        issuer = self.decode_token(token=token, verify_signature=False).get("iss")
        assert issuer in self.recognised_issuers, f"Unrecognised issuer: `{issuer}`"
        issuer_certs_url = f"{issuer}/protocol/openid-connect/certs"
        response = requests.get(url=issuer_certs_url)
        if response.status_code != status.HTTP_200_OK:
            raise ServerError(
                f"Error {response.status_code} from OIDC Auth Server ({issuer_certs_url}): {response.text}")
        jwks = response.json()
        public_keys = {}
        for jwk in jwks['keys']:
            kid = jwk['kid']
            public_keys[kid] = RSAAlgorithm.from_jwk(json.dumps(jwk))
        kid = jwt.get_unverified_header(token)['kid']
        key = public_keys.get(kid)
        decoded = self.decode_token(token=token, key=key, issuer=issuer, audience=self.get_oidc_config(issuer)["audiences"])
        return super().retrieve_username(token_payload=decoded)

    def logout_user(self, payload: bytes, access_token: str):
        try:
            refresh_token = json.loads(payload).get("refresh_token")
        except json.JSONDecodeError as e:
            raise RequestException(f"Logout request missing `refresh_token` - {e}")
        issuer = self.decode_token(token=refresh_token, verify_signature=False).get("iss")
        response = requests.post(url=self.logout_url(issuer),
                                 data={**self.client_identity(issuer),
                                       "refresh_token": refresh_token},
                                 headers={"Authorization": f"Bearer {access_token}"})
        if response.status_code != status.HTTP_204_NO_CONTENT:
            raise RequestException(f"Error during logout: {response.text}")


class JWTAuth(Auth):
    USERNAME_LOOKUP = "username"
    tokens_class = JWTAuthTokens
    server_url = env("JWT_SERVER_URL")
    server_headers = {"X-User-App": env("JWT_APP_NAME")}
    signing_key = env("JWT_SIGNING_KEY")
    leeway = 15

    @property
    def token_url(self):
        return f"{self.server_url}/jwt/"

    @property
    def refresh_url(self):
        return f"{self.server_url}/jwt/refresh/"

    def get_tokens(self, username: str, password: str) -> AuthTokens:
        data = {"username": username,
                "password": password
                }
        return super().get_tokens(url=self.token_url, data=data, headers=self.server_headers)

    def refresh_token(self, token: str):
        return super().refresh_token(url=self.refresh_url,
                                     data={"refresh": token},
                                     headers=self.server_headers)

    def authenticate(self, token: str) -> str:
        decoded = self.decode_token(token=token, key=self.signing_key, leeway=self.leeway)
        return super().retrieve_username(token_payload=decoded)

    def logout_user(self, *args):
        pass


oidc_auth = OIDCAuth()
jwt_auth = JWTAuth()


class AuthService:
    authenticators = {settings.OIDC_AUTH_MODE: oidc_auth,
                      settings.JWT_AUTH_MODE: jwt_auth
                      }
    applicative_users = {env("ROLLOUT_TOKEN"): settings.ROLLOUT_USERNAME,
                         **getattr(settings, "APPLICATIVE_USERS", {})}

    def __init__(self):
        self.post_auth_hooks: List[Callable[[User, str, Dict[str, str]], Optional[User]]] = []

    def add_post_authentication_hook(self, callback: Callable[[User, str, Dict[str, str]], Optional[User]]):
        self.post_auth_hooks += [callback]

    def _get_authenticator(self, auth_method: str):
        try:
            return self.authenticators[auth_method]
        except KeyError as ke:
            _logger.error(f"Invalid authentication method : {auth_method}")
            raise ke

    def get_tokens(self, **params) -> AuthTokens:
        for authenticator in self.authenticators.values():
            authenticator_signature = inspect.signature(authenticator.get_tokens)
            try:
                authenticator_signature.bind(**params)
            except TypeError:
                continue
            return authenticator.get_tokens(**params)

    def refresh_token(self, request) -> Union[dict, None]:
        _, auth_method = self.get_auth_data(request)
        token = json.loads(request.body).get('refresh_token')
        authenticator = self._get_authenticator(auth_method)
        return authenticator.refresh_token(token=token)

    def logout_user(self, request):
        access_token, auth_method = self.get_auth_data(request)
        authenticator = self._get_authenticator(auth_method)
        authenticator.logout_user(request.body, access_token)
        logout(request)

    def authenticate_token(self, token: str, auth_method: str, headers: Dict[str, str]) -> Union[Tuple[User, str], None]:
        assert auth_method is not None, "Missing `auth_method` parameter"
        if token is None:
            return None
        try:
            authenticator = self._get_authenticator(auth_method)
            username = authenticator.authenticate(token=token)
            user = User.objects.get(username=username)
            for post_auth_hook in self.post_auth_hooks:
                user = post_auth_hook(user, token, headers)
            return user, token
        except (InvalidTokenError, ValueError, User.DoesNotExist):
            return None

    def authenticate_http_request(self, request) -> Union[Tuple[User, str], None]:
        token, auth_method = self.get_auth_data(request)
        if token in self.applicative_users:
            applicative_user = User.objects.get(username=self.applicative_users[token])
            return applicative_user, token
        return self.authenticate_token(token=token, auth_method=auth_method or settings.JWT_AUTH_MODE, headers=request.headers)

    def authenticate_ws_request(self, token: str, auth_method: str, headers: Dict[str, str]) -> Union[User, None]:
        res = self.authenticate_token(token=token, auth_method=auth_method, headers=headers)
        if res is not None:
            return res[0]
        _logger.info("Error authenticating WS request")

    def retrieve_username(self, token: str, auth_method: str) -> str:
        authenticator = self._get_authenticator(auth_method)
        decoded = authenticator.decode_token(token=token, verify_signature=False)
        return authenticator.retrieve_username(decoded)

    def get_auth_data(self, request) -> Tuple[str, str]:
        auth_token, auth_method = self.get_token_from_headers(request)
        if not auth_token:
            auth_token = request.COOKIES.get(settings.ACCESS_TOKEN_COOKIE)
        return auth_token, auth_method

    def get_token_from_headers(self, request) -> Tuple[Union[str, None], Union[str, None]]:
        authorization = request.META.get('HTTP_AUTHORIZATION')
        authorization_method = request.META.get('HTTP_AUTHORIZATIONMETHOD')
        if isinstance(authorization, str):
            authorization = authorization.encode(HTTP_HEADER_ENCODING)
        if authorization is None:
            return None, None
        return self.get_raw_token(authorization), authorization_method

    @staticmethod
    def get_raw_token(header: bytes) -> Union[str, None]:
        parts = header.split()
        if not parts:
            return None
        if parts[0] not in AUTH_HEADER_TYPE_BYTES:
            return None
        if len(parts) != 2:
            raise AuthenticationFailed(code='bad_authorization_header',
                                       detail='Authorization header must contain two space-delimited values')
        res = parts[1]
        return res if not isinstance(res, bytes) else res.decode('utf-8')


auth_service = AuthService()
