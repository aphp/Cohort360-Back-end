import inspect
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Union, Tuple, Optional, Callable, Dict, List

import environ
import jwt
import requests
from django.apps import apps
from django.conf import settings
from django.contrib.auth import logout
from django.utils.module_loading import import_string
from jwt import InvalidTokenError
from jwt.algorithms import RSAAlgorithm
from requests import RequestException
from rest_framework import status, HTTP_HEADER_ENCODING
from rest_framework.exceptions import AuthenticationFailed

from admin_cohort.models import User
from admin_cohort.types import ServerError, LoginError, OIDCAuthTokens, JWTAuthTokens, AuthTokens

env = environ.Env()
_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')

extra_applicative_users = {}

if apps.is_installed("cohort_job_server"):
    from cohort_job_server.apps import CohortJobServerConfig
    extra_applicative_users = CohortJobServerConfig.APPLICATIVE_USERS_TOKENS


class Auth(ABC):
    USERNAME_LOOKUP = None
    tokens_class = None

    def __init__(self):
        assert self.USERNAME_LOOKUP is not None, "`USERNAME_LOOKUP` attribute is not defined"
        assert self.tokens_class is not None, "`tokens_class` attribute is not defined"
        self.algorithms = env("JWT_ALGORITHMS", default="RS256,HS256")

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
            raise InvalidTokenError("Token is invalid or has expired")
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


@dataclass
class OIDCAuthConfig:
    issuer: str
    client_id: str
    client_secret: str
    grant_type: str
    redirect_uri: str

    @property
    def client_identity(self) -> dict[str, str]:
        return {"client_id": self.client_id,
                "client_secret": self.client_secret
                }

    @property
    def oidc_url(self):
        return f"{self.issuer}/protocol/openid-connect"

    @property
    def token_url(self):
        return f"{self.oidc_url}/token"

    @property
    def logout_url(self):
        return f"{self.oidc_url}/logout"


def build_oidc_configs() -> List[OIDCAuthConfig]:
    configs = []
    i = 1
    while True:
        issuer = env(f"OIDC_AUTH_SERVER_{i}", default=None)
        if issuer is not None:
            configs.append(OIDCAuthConfig(issuer=issuer,
                                          client_id=env(f"OIDC_CLIENT_ID_{i}"),
                                          client_secret=env(f"OIDC_CLIENT_SECRET_{i}"),
                                          grant_type=env(f"OIDC_GRANT_TYPE_{i}"),
                                          redirect_uri=env(f"OIDC_REDIRECT_URI_{i}")))
            i += 1
        else:
            break
    return configs


class OIDCAuth(Auth):
    USERNAME_LOOKUP = "preferred_username"
    tokens_class = OIDCAuthTokens

    def __init__(self):
        super().__init__()
        self.oidc_extra_allowed_servers = env("OIDC_EXTRA_SERVER_URLS", default="").split(",")
        self.audience = env("OIDC_AUDIENCE", default="").split(',')
        self.refresh_grant_type = "refresh_token"
        self.oidc_configs = build_oidc_configs()

    def get_oidc_config(self, client_id: Optional[str] = None, redirect_uri: Optional[str] = None):
        if not self.oidc_configs:
            raise ValueError("No OIDC auth config was provided")
        if client_id and redirect_uri:
            raise ValueError("Provide one of `issuer` or `redirect_uri`, not both!")
        if client_id:
            attr, val = "client_id", client_id
        elif redirect_uri:
            attr, val = "redirect_uri", redirect_uri
        else:
            _logger.warning("No `client_id` or `redirect_uri` provided, using first OIDC config")
            return self.oidc_configs[0]
        return next((conf for conf in self.oidc_configs if getattr(conf, attr, None) == val))

    @property
    def recognised_issuers(self):
        return [c.issuer for c in self.oidc_configs] + self.oidc_extra_allowed_servers

    def get_tokens(self, code: str, redirect_uri: Optional[str] = None) -> AuthTokens:
        oidc_conf = self.get_oidc_config(redirect_uri=redirect_uri)
        data = {**oidc_conf.client_identity,
                "redirect_uri": oidc_conf.redirect_uri,
                "grant_type": oidc_conf.grant_type,
                "code": code
                }
        return super().get_tokens(url=oidc_conf.token_url, data=data)

    def refresh_token(self, token: str):
        client_id = self.decode_token(token=token, verify_signature=False).get("azp")
        oidc_conf = self.get_oidc_config(client_id)
        data = {**oidc_conf.client_identity,
                "grant_type": self.refresh_grant_type,
                "refresh_token": token}
        return super().refresh_token(url=oidc_conf.token_url, data=data)

    def authenticate(self, token: str) -> str:
        decoded_token = self.decode_token(token=token, verify_signature=False)
        issuer = decoded_token.get("iss")
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
        decoded = self.decode_token(token=token, key=key, issuer=issuer, audience=self.audience)
        return super().retrieve_username(token_payload=decoded)

    def logout_user(self, payload: bytes, access_token: str):
        try:
            refresh_token = json.loads(payload).get("refresh_token")
        except json.JSONDecodeError as e:
            raise RequestException(f"Logout request missing `refresh_token` - {e}")
        client_id = self.decode_token(token=refresh_token, verify_signature=False).get("azp")
        oidc_conf = self.get_oidc_config(client_id)
        response = requests.post(url=oidc_conf.logout_url,
                                 data={**oidc_conf.client_identity,
                                       "refresh_token": refresh_token},
                                 headers={"Authorization": f"Bearer {access_token}"})
        if response.status_code != status.HTTP_204_NO_CONTENT:
            raise RequestException(f"Error during logout: {response.text}")


class JWTAuth(Auth):
    USERNAME_LOOKUP = "username"
    tokens_class = JWTAuthTokens
    leeway = 15

    def __init__(self):
        super().__init__()
        self.server_url = env.url("JWT_SERVER_URL", default="")
        self.server_headers = {"X-User-App": env.str("JWT_APP_NAME", default="")}
        self.signing_key = env.str("JWT_SIGNING_KEY", default="")

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


class AuthService:
    authenticators = {settings.OIDC_AUTH_MODE: OIDCAuth(),
                      **({settings.JWT_AUTH_MODE: JWTAuth()} if settings.ENABLE_JWT else {})
                      }
    applicative_users = {env("ROLLOUT_TOKEN", default=""): env("ROLLOUT_USERNAME", default="ROLLOUT_PIPELINE"),
                         **extra_applicative_users
                         }

    def __init__(self):
        self.post_auth_hooks: List[Callable[[User, Dict[str, str]], Optional[User]]] = self.load_post_auth_hooks()

    @staticmethod
    def load_post_auth_hooks():
        post_auth_hooks = []
        for app in settings.INCLUDED_APPS:
            hooks = getattr(apps.get_app_config(app), "POST_AUTH_HOOKS", list())
            for hook_path in hooks:
                hook = import_string(hook_path)
                if hook:
                    post_auth_hooks.append(hook)
                else:
                    _logger.warning(f"Improperly configured post authentication hook `{hook_path}`")
        return post_auth_hooks

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

    def authenticate_token(self, token: str, auth_method: str, headers: Dict[str, str]) -> Union[
        Tuple[User, str], None]:
        assert auth_method is not None, "Missing `auth_method` parameter"
        if token is None:
            return None
        try:
            authenticator = self._get_authenticator(auth_method)
            username = authenticator.authenticate(token=token)
            user = User.objects.get(username=username)
            for post_auth_hook in self.post_auth_hooks:
                user = post_auth_hook(user, headers)
            return user, token
        except (InvalidTokenError, ValueError, User.DoesNotExist) as e:
            _logger.error(f"Error authenticating token: {e}")
            return None

    def authenticate_http_request(self, request) -> Union[Tuple[User, str], None]:
        token, auth_method = self.get_auth_data(request)
        if token in self.applicative_users:
            applicative_user = User.objects.get(username=self.applicative_users[token])
            return applicative_user, token
        return self.authenticate_token(token=token, auth_method=auth_method or settings.OIDC_AUTH_MODE,
                                       headers=request.headers)

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
        if parts[0] != "Bearer".encode(HTTP_HEADER_ENCODING):
            return None
        if len(parts) != 2:
            raise AuthenticationFailed(code='bad_authorization_header',
                                       detail='Authorization header must contain two space-delimited values')
        res = parts[1]
        token = res if not isinstance(res, bytes) else res.decode('utf-8')
        return token


auth_service = AuthService()
