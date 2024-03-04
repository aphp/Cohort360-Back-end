import inspect
import json
import logging
from abc import ABC, abstractmethod
from typing import Union, Tuple

import environ
import jwt
import requests
from django.contrib.auth import logout
from jwt import InvalidTokenError
from jwt.algorithms import RSAAlgorithm
from requests import RequestException
from rest_framework import status, HTTP_HEADER_ENCODING
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import AUTH_HEADER_TYPE_BYTES
from rest_framework_simplejwt.exceptions import InvalidToken

from admin_cohort.models import User
from admin_cohort.settings import JWT_AUTH_MODE, OIDC_AUTH_MODE, ETL_USERNAME, SJS_USERNAME, ROLLOUT_USERNAME, ACCESS_TOKEN_COOKIE
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
    server_aphp_url = env("OIDC_SERVER_APHP_URL")
    audience = env("OIDC_AUDIENCES").split(';')
    redirect_uri = env("OIDC_REDIRECT_URI")
    grant_type = env("OIDC_GRANT_TYPE")
    refresh_grant_type = "refresh_token"
    server_master_url = env("OIDC_SERVER_MASTER_URL")
    server_root_url = f"{server_aphp_url}/protocol/openid-connect"

    @property
    def client_identity(self):
        return {"client_id": env("OIDC_CLIENT_ID"),
                "client_secret": env("OIDC_CLIENT_SECRET")
                }

    @property
    def recognised_issuers(self):
        return [self.server_aphp_url,
                self.server_master_url]

    @property
    def token_url(self):
        return f"{self.server_root_url}/token"

    @property
    def logout_url(self):
        return f"{self.server_root_url}/logout"

    def get_tokens(self, code: str) -> AuthTokens:
        data = {**self.client_identity,
                "redirect_uri": self.redirect_uri,
                "grant_type": self.grant_type,
                "code": code
                }
        return super().get_tokens(url=self.token_url, data=data)

    def refresh_token(self, token: str):
        data = {**self.client_identity,
                "grant_type": self.refresh_grant_type,
                "refresh_token": token}
        return super().refresh_token(url=self.token_url, data=data)

    def authenticate(self, token: str) -> str:
        issuer = self.decode_token(token=token, verify_signature=False).get("iss")
        assert issuer in self.recognised_issuers, f"Unrecognised issuer: `{issuer}`"
        issuer_certs_url = f"{issuer}/protocol/openid-connect/certs"
        response = requests.get(url=issuer_certs_url)
        if response.status_code != status.HTTP_200_OK:
            raise ServerError(f"Error {response.status_code} from OIDC Auth Server ({issuer_certs_url}): {response.text}")
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
        response = requests.post(url=self.logout_url,
                                 data={**self.client_identity,
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
    authenticators = {OIDC_AUTH_MODE: oidc_auth,
                      JWT_AUTH_MODE: jwt_auth
                      }
    applicative_users = {env("ETL_TOKEN"): ETL_USERNAME,
                         env("SJS_TOKEN"): SJS_USERNAME,
                         env("ROLLOUT_MAINTENANCE_TOKEN"): ROLLOUT_USERNAME
                         }

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

    def authenticate_token(self, token: str, auth_method: str) -> Union[Tuple[User, str], None]:
        assert auth_method is not None, "Missing `auth_method` parameter"
        if token is None:
            return None
        try:
            authenticator = self._get_authenticator(auth_method)
            username = authenticator.authenticate(token=token)
            user = User.objects.get(username=username)
        except (InvalidTokenError, ValueError, User.DoesNotExist):
            return None
        return user, token

    def authenticate_http_request(self, request) -> Union[Tuple[User, str], None]:
        token, auth_method = self.get_auth_data(request)
        if token in self.applicative_users:
            applicative_user = User.objects.get(username=self.applicative_users[token])
            return applicative_user, token
        return self.authenticate_token(token=token, auth_method=auth_method or JWT_AUTH_MODE)

    def authenticate_ws_request(self, token: str, auth_method: str) -> Union[User, None]:
        res = self.authenticate_token(token=token, auth_method=auth_method)
        if res is not None:
            return res[0]
        _logger_err.exception("Error authenticating WS request")

    def retrieve_username(self, token: str, auth_method: str) -> str:
        authenticator = self._get_authenticator(auth_method)
        decoded = authenticator.decode_token(token=token, verify_signature=False)
        return authenticator.retrieve_username(decoded)

    def get_auth_data(self, request) -> Tuple[str, str]:
        auth_token, auth_method = self.get_token_from_headers(request)
        if not auth_token:
            auth_token = request.COOKIES.get(ACCESS_TOKEN_COOKIE)
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
