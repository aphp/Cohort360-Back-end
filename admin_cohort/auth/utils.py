import json
import logging
from json import JSONDecodeError
from typing import Union, Tuple

import environ
import jwt
import requests
from django.contrib.auth import logout as auth_logout
from requests import RequestException
from rest_framework import status, HTTP_HEADER_ENCODING
from rest_framework_simplejwt.authentication import AUTH_HEADER_TYPE_BYTES
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from admin_cohort.models import User
from admin_cohort.settings import JWT_AUTH_MODE, OIDC_AUTH_MODE, ACCESS_TOKEN_COOKIE
from admin_cohort.types import ServerError, AuthTokens, LoginError, UserInfo

env = environ.Env()

AUTH_SERVER_APP_HEADER = "X-User-App"
APP_NAME = env("JWT_APP_NAME")

JWT_SERVER_HEADERS = {AUTH_SERVER_APP_HEADER: APP_NAME}

JWT_SERVER_URL = env("JWT_SERVER_URL")
JWT_SERVER_TOKEN_URL = f"{JWT_SERVER_URL}/jwt/"
JWT_SERVER_REFRESH_URL = f"{JWT_SERVER_URL}/jwt/refresh/"
JWT_SERVER_USERINFO_URL = f"{JWT_SERVER_URL}/jwt/user_info/"
JWT_SIGNING_KEY = env("JWT_SIGNING_KEY")

JWT_ALGORITHMS = env("JWT_ALGORITHMS").split(',')

OIDC_SERVER_MASTER_URL = env("OIDC_SERVER_MASTER_URL")

OIDC_SERVER_APHP_URL = env("OIDC_SERVER_APHP_URL")
OIDC_SERVER_TOKEN_URL = f"{OIDC_SERVER_APHP_URL}/protocol/openid-connect/token"
OIDC_SERVER_LOGOUT_URL = f"{OIDC_SERVER_APHP_URL}/protocol/openid-connect/logout"

OIDC_AUDIENCES = env("OIDC_AUDIENCES").split(';')
OIDC_CLIENT_ID = env("OIDC_CLIENT_ID")
OIDC_CLIENT_SECRET = env("OIDC_CLIENT_SECRET")
OIDC_GRANT_TYPE = env("OIDC_GRANT_TYPE")
OIDC_REDIRECT_URI = env("OIDC_REDIRECT_URI")

_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')


def get_jwt_tokens(username: str, password: str) -> AuthTokens:
    resp = requests.post(url=JWT_SERVER_TOKEN_URL,
                         data={"username": username,
                               "password": password},
                         headers=JWT_SERVER_HEADERS)
    if resp.status_code == status.HTTP_401_UNAUTHORIZED:
        raise LoginError("Invalid username or password")
    if resp.status_code != status.HTTP_200_OK:
        raise ServerError(f"Error {resp.status_code} from authentication server: {resp.text}")
    return AuthTokens(**resp.json())


def get_oidc_tokens(code):
    data = {"client_id": OIDC_CLIENT_ID,
            "client_secret": OIDC_CLIENT_SECRET,
            "redirect_uri": OIDC_REDIRECT_URI,
            "grant_type": OIDC_GRANT_TYPE,
            "code": code
            }
    response = requests.post(url=OIDC_SERVER_TOKEN_URL, data=data)
    return AuthTokens(**response.json())


def extract_username_from_token(access_token: str):
    decoded = jwt.decode(jwt=access_token,
                         algorithms=JWT_ALGORITHMS,
                         options={'verify_signature': False})
    return decoded.get("preferred_username")


def refresh_jwt_token(token: str):
    return requests.post(url=JWT_SERVER_REFRESH_URL,
                         data={"refresh": token},
                         headers=JWT_SERVER_HEADERS)


def refresh_oidc_token(token: str):
    return requests.post(url=OIDC_SERVER_TOKEN_URL,
                         data={"client_id": OIDC_CLIENT_ID,
                               "client_secret": OIDC_CLIENT_SECRET,
                               "grant_type": "refresh_token",
                               "refresh_token": token})


def logout_user(request):
    access_token, auth_mode = get_auth_data(request)
    if auth_mode not in (JWT_AUTH_MODE, OIDC_AUTH_MODE):
        _logger.error(f"Invalid AUTHORIZATIONMETHOD header `{auth_mode}` to logout user `{request.user}`")
    if auth_mode == OIDC_AUTH_MODE:
        try:
            refresh_token = json.loads(request.body).get("refresh_token")
        except JSONDecodeError as e:
            raise RequestException(f"Logout request missing `refresh_token` - {e}")
        response = requests.post(url=OIDC_SERVER_LOGOUT_URL,
                                 data={"client_id": OIDC_CLIENT_ID,
                                       "client_secret": OIDC_CLIENT_SECRET,
                                       "refresh_token": refresh_token},
                                 headers={"Authorization": f"Bearer {access_token}"})
        if response.status_code != status.HTTP_204_NO_CONTENT:
            raise RequestException(f"Error during logout: {response.text}")
    auth_logout(request)


def decode_oidc_token(token: str, issuer: str):
    issuer_certs_url = f"{issuer}/protocol/openid-connect/certs"
    resp = requests.get(url=issuer_certs_url)
    if resp.status_code != status.HTTP_200_OK:
        raise ServerError(f"Error {resp.status_code} from OIDC Auth Server ({issuer_certs_url}): {resp.text}")
    jwks = resp.json()
    public_keys = {}
    for jwk in jwks['keys']:
        kid = jwk['kid']
        public_keys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))

    kid = jwt.get_unverified_header(token)['kid']
    key = public_keys.get(kid)
    return jwt.decode(jwt=token,
                      key=key,
                      verify=True,
                      issuer=issuer,
                      algorithms=JWT_ALGORITHMS,
                      audience=OIDC_AUDIENCES)


def get_token_issuer(token: str) -> str:
    decoded = jwt.decode(jwt=token,
                         algorithms=JWT_ALGORITHMS,
                         options={'verify_signature': False})
    issuer = decoded.get("iss")
    assert issuer in (OIDC_SERVER_APHP_URL, OIDC_SERVER_MASTER_URL), f"Unknown issuer: `{issuer}`"
    return issuer


def get_userinfo_from_token(token: str, auth_method: str) -> Union[None, UserInfo]:
    if token == env("ETL_TOKEN"):
        _logger.info("ETL token connexion")
        return UserInfo.solr()
    if token == env("SJS_TOKEN"):
        _logger.info("SJS token connexion")
        return UserInfo.sjs()
    if token == env("ROLLOUT_MAINTENANCE_TOKEN"):
        return UserInfo.rollout()

    if auth_method == JWT_AUTH_MODE:
        try:
            decoded = jwt.decode(token, key=JWT_SIGNING_KEY, algorithms=JWT_ALGORITHMS, leeway=15)
            user = User.objects.get(pk=decoded["username"])
            return UserInfo(username=user.username,
                            firstname=user.firstname,
                            lastname=user.lastname,
                            email=user.email)
        except User.DoesNotExist as e:
            raise ServerError(f"Error verifying token. User not found - {e}")
    elif auth_method == OIDC_AUTH_MODE:
        try:
            issuer = get_token_issuer(token=token)
            decoded = decode_oidc_token(token=token, issuer=issuer)
            return UserInfo(username=decoded.get('preferred_username'),
                            firstname=decoded.get('name'),
                            lastname=decoded.get('family_name'),
                            email=decoded.get('email'))
        except Exception as e:
            _logger.info(f"Error decoding token: {e} - `{token}`")
            raise e
    else:
        raise ValueError(f"Invalid authentication method : {auth_method}")


def get_auth_data(request) -> Tuple[str, str]:
    auth_token, auth_method = get_token_from_headers(request)
    if not auth_token:
        auth_token = request.COOKIES.get(ACCESS_TOKEN_COOKIE)
    return auth_token, auth_method


def get_token_from_headers(request) -> Tuple[Union[str, None], Union[str, None]]:
    authorization = request.META.get('HTTP_AUTHORIZATION')
    authorization_method = request.META.get('HTTP_AUTHORIZATIONMETHOD')
    if isinstance(authorization, str):
        authorization = authorization.encode(HTTP_HEADER_ENCODING)
    if authorization is None:
        return None, None
    return get_raw_token(authorization), authorization_method


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
