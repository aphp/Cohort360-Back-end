import hashlib
import json
import logging
from abc import ABC
from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache
from typing import Tuple, Optional, Callable, Dict, List

import environ
import jwt
import requests
from django.apps import apps
from django.conf import settings
from django.contrib.auth import authenticate
from django.utils import timezone
from django.utils.module_loading import import_string
from jwt import InvalidTokenError
from jwt.algorithms import RSAAlgorithm
from requests import RequestException
from rest_framework import status, HTTP_HEADER_ENCODING
from rest_framework.exceptions import AuthenticationFailed, ValidationError, APIException
from rest_framework_simplejwt.serializers import TokenRefreshSerializer, TokenObtainPairSerializer
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from accesses.models import Profile, Role, Perimeter, Access
from admin_cohort.apps import AdminCohortConfig
from admin_cohort.models import User
from admin_cohort.types import OIDCAuthTokens, JWTAuthTokens, AuthTokens
from admin_cohort.exceptions import ServerError, NoAuthenticationHookDefined


env = environ.Env()
_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')

extra_applicative_users = {}

if apps.is_installed("cohort_job_server"):
    from cohort_job_server.apps import CohortJobServerConfig
    extra_applicative_users = CohortJobServerConfig.APPLICATIVE_USERS_TOKENS


class Auth(ABC):
    USERNAME_LOOKUP = None

    def __init__(self):
        assert self.USERNAME_LOOKUP is not None, "`USERNAME_LOOKUP` attribute is not defined"
        self.algorithms = env("JWT_ALGORITHMS", default="RS256,HS256")

    def logout(self, *args):
        # JWT based auth does not do extra logout logic.
        # the 'logout' from 'django.contrib.auth' module is called from the logout view
        pass

    def decode_token(self, token: str, verify_signature=True, key="", issuer=None, audience=None):
        options = {'verify_signature': verify_signature}
        kwargs = {'algorithms': self.algorithms,
                  'key': key,
                  'issuer': issuer,
                  'audience': audience
                  }
        try:
            return jwt.decode(jwt=token, options=options, **kwargs)
        except jwt.PyJWTError as e:
            _logger.info(f"Error decoding token: {e}")
            raise e


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
                                          grant_type="authorization_code",
                                          redirect_uri=env(f"OIDC_REDIRECT_URI_{i}")))
            i += 1
        else:
            break
    return configs


@lru_cache
def get_issuer_certs(issuer: str) -> dict:
    issuer_certs_url = f"{issuer}/protocol/openid-connect/certs"
    response = requests.get(url=issuer_certs_url)
    if response.status_code != status.HTTP_200_OK:
        raise ServerError(f"Error {response.status_code} from OIDC Auth Server ({issuer_certs_url}): {response.text}")
    jwks = response.json()
    certs = {}
    for jwk in jwks['keys']:
        kid = jwk['kid']
        certs[kid] = RSAAlgorithm.from_jwk(json.dumps(jwk))
    return certs


class OIDCAuth(Auth):
    USERNAME_LOOKUP = "preferred_username"

    def __init__(self):
        super().__init__()
        self.oidc_extra_allowed_servers = env("OIDC_EXTRA_SERVER_URLS", default="").split(",")
        self.audience = env("OIDC_AUDIENCE", default="").split(',')
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

    def get_tokens(self, code: str, redirect_uri: Optional[str] = None) -> Optional[OIDCAuthTokens]:
        oidc_conf = self.get_oidc_config(redirect_uri=redirect_uri)
        data = {**oidc_conf.client_identity,
                "redirect_uri": oidc_conf.redirect_uri,
                "grant_type": oidc_conf.grant_type,
                "code": code
                }
        try:
            response = requests.post(url=oidc_conf.token_url, data=data)
            if response.status_code == status.HTTP_200_OK:
                return OIDCAuthTokens(**response.json())
            return None
        except Exception as e:
            raise ServerError(f"Error issuing tokens: {e}")

    def refresh_token(self, token: str) -> Optional[OIDCAuthTokens]:
        client_id = self.decode_token(token=token, verify_signature=False).get("azp")
        oidc_conf = self.get_oidc_config(client_id)
        data = {**oidc_conf.client_identity,
                "grant_type": "refresh_token",
                "refresh_token": token
                }
        try:
            response = requests.post(url=oidc_conf.token_url, data=data)
            if response.status_code == status.HTTP_200_OK:
                return OIDCAuthTokens(**response.json())
            raise InvalidToken("Token is invalid or expired")
        except InvalidTokenError as e:
            raise e
        except Exception as e:
            raise ServerError(f"Error refreshing token: {e}")

    def authenticate(self, token: str) -> str:
        decoded_token = self.decode_token(token=token, verify_signature=False)
        issuer = decoded_token.get("iss")
        assert issuer in self.recognised_issuers, f"Unrecognised issuer: `{issuer}`"
        certs = get_issuer_certs(issuer=issuer)
        kid = jwt.get_unverified_header(token)['kid']
        key = certs.get(kid)
        decoded = self.decode_token(token=token, key=key, issuer=issuer, audience=self.audience)
        return decoded.get(self.USERNAME_LOOKUP)

    def retrieve_username(self, token: str) -> str:
        decoded = self.decode_token(token=token, verify_signature=False)
        return decoded.get(self.USERNAME_LOOKUP)

    @staticmethod
    def login(request) -> User:
        try:
            code = request.data["auth_code"]
            redirect_uri = request.data["redirect_uri"]
        except KeyError as e:
            raise AuthenticationFailed(f"Missing `{e}`")
        user = authenticate(request=request, code=code, redirect_uri=redirect_uri)
        return user

    def logout(self, payload: dict, access_token: str):
        try:
            refresh_token = payload.get("refresh_token")
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

    def __init__(self):
        super().__init__()
        self.signing_key = settings.SIMPLE_JWT.get("SIGNING_KEY")

    def authenticate(self, token: str) -> str:
        decoded = self.decode_token(token=token, key=self.signing_key)
        return decoded.get(self.USERNAME_LOOKUP)

    @staticmethod
    def login(request) -> User:
        serializer = TokenObtainPairSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except (TokenError, AuthenticationFailed) as e:
            raise AuthenticationFailed(e.args[0])
        user, auth_tokens = serializer.user, serializer.validated_data
        request.auth_tokens = JWTAuthTokens(**auth_tokens)
        return user

    @staticmethod
    def refresh_token(token: str) -> Optional[JWTAuthTokens]:
        serializer = TokenRefreshSerializer(data={"refresh": token})
        try:
            serializer.is_valid(raise_exception=True)
        except (ValidationError, TokenError) as e:
            raise InvalidToken(e.args[0])
        return JWTAuthTokens(**serializer.validated_data)

    def check_credentials(self, username, password) -> Optional[bool]:
        """
        if an external Identity Server is configured, reach out to it.
        otherwise, validate credentials inplace.
        :param username:
        :param password:
        :return: boolean to indicate if the credentials are valid
        """
        try:
            _ = User.objects.get(username=username)
        except User.DoesNotExist:
            raise AuthenticationFailed(f"User `{username}` does not exist")

        try:
            _logger.info("[Authentication] Attempting authentication with external services")
            return self.authenticate_with_external_services(username=username, password=password)
        except NoAuthenticationHookDefined:
            _logger.info("[Authentication] Fallback to local authentication")
            return self.check_credentials_locally(username=username, password=password)

    @staticmethod
    def authenticate_with_external_services(username, password) -> Optional[bool]:
        authentication_hooks = AdminCohortConfig.HOOKS.get("USER_AUTHENTICATION", [])
        if not authentication_hooks:
            raise NoAuthenticationHookDefined()
        for auth_hook in authentication_hooks:
            try:
                auth_hook = import_string(auth_hook)
                authenticated = auth_hook(username=username, password=password)
                if authenticated:
                    return True
            except ImportError as e:
                _logger.error(f"[Authentication] hook improperly configured: {str(e)}")
            except APIException:
                continue
        _logger.error("[Authentication] All external services failed. Review defined hooks or remove them")
        return False


    @staticmethod
    def check_credentials_locally(username, password):
        hashed_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
        user = User.objects.get(username=username)
        return user.password == hashed_password

    @staticmethod
    def generate_system_token() -> str:
        """
        Generate a system JWT token for internal API calls.
        @returns: str: The generated access token
        """
        system_user, created = User.objects.get_or_create(username="system",
                                                          defaults={"username": "system",
                                                                    "firstname": "System",
                                                                    "lastname": "SYSTEM",
                                                                    "email": "system.dj@aphp.fr"
                                                                    })
        if created:
            p = Profile.objects.create(user_id=system_user.username, is_active=True)
            root_perimeter = Perimeter.objects.get(pk=settings.ROOT_PERIMETER_ID)
            admin_role = Role.objects.filter(right_full_admin=True).first()
            now = timezone.now()
            Access.objects.create(profile=p,
                                  perimeter=root_perimeter,
                                  role=admin_role,
                                  start_datetime=now,
                                  end_datetime=now + timedelta(weeks=52 * 100)  # grant access forever
                                  )
            _logger.info(f"System user created and granted `{admin_role.name}` role on perimeter `{root_perimeter.name}`")
        try:
            serializer = TokenObtainPairSerializer()
            token = serializer.get_token(system_user)
            return str(token.access_token)
        except Exception as e:
            _logger_err.error(f"Failed to generate system token: {e}")
            raise ServerError(f"Error generating system token: {e}")


class AuthService:
    authenticators = {settings.JWT_AUTH_MODE: JWTAuth(),
                      **({settings.OIDC_AUTH_MODE: OIDCAuth()} if settings.ENABLE_OIDC_AUTH else {})
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
            hooks = getattr(apps.get_app_config(app), "POST_AUTH_HOOKS", [])
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

    def refresh_token(self, request) -> Optional[AuthTokens]:
        _, auth_method = self.get_token_from_headers(request)
        authenticator = self._get_authenticator(auth_method)
        token = request.data.get('refresh_token')
        return authenticator.refresh_token(token=token)

    def login(self, request, auth_method: str) -> User:
        authenticator = self._get_authenticator(auth_method)
        return authenticator.login(request=request)

    def logout(self, request):
        access_token, auth_method = self.get_token_from_headers(request)
        authenticator = self._get_authenticator(auth_method)
        authenticator.logout(request.data, access_token)

    def authenticate_request(self, token: str, auth_method: str, headers: Dict[str, str]) -> Optional[Tuple[User, str]]:
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
            _logger.error(f"Error authenticating request: {e}")
            return None

    def authenticate_http_request(self, request) -> Optional[Tuple[User, str]]:
        token, auth_method = self.get_token_from_headers(request)
        if token in self.applicative_users:
            applicative_user = User.objects.get(username=self.applicative_users[token])
            return applicative_user, token
        return self.authenticate_request(token=token, auth_method=auth_method, headers=request.headers)

    def authenticate_ws_request(self, token: str, auth_method: str, headers: Dict[str, str]) -> Optional[User]:
        res = self.authenticate_request(token=token, auth_method=auth_method, headers=headers)
        if res is not None:
            return res[0]
        _logger.info("Error authenticating WS request")

    def get_token_from_headers(self, request) -> Tuple[Optional[str], Optional[str]]:
        authorization = request.META.get('HTTP_AUTHORIZATION')
        authorization_method = request.META.get(f"HTTP_{settings.AUTHORIZATION_METHOD_HEADER}")
        if isinstance(authorization, str):
            authorization = authorization.encode(HTTP_HEADER_ENCODING)
        if authorization is None:
            return None, None
        return self.get_raw_token(authorization), authorization_method

    @staticmethod
    def get_raw_token(header: bytes) -> Optional[str]:
        parts = header.split()
        if not parts:
            return None
        if len(parts) != 2:
            raise AuthenticationFailed(code='bad_authorization_header',
                                       detail='Authorization header must contain two space-delimited values')
        if parts[0] != "Bearer".encode(HTTP_HEADER_ENCODING):
            return None
        res = parts[1]
        token = res if not isinstance(res, bytes) else res.decode('utf-8')
        return token


auth_service = AuthService()
oidc_auth_service = OIDCAuth()
jwt_auth_service = JWTAuth()
