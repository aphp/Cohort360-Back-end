import json
import logging
from typing import Optional, Union

import environ
import jwt
import requests
from django.contrib.auth import logout as auth_logout
from jwt import DecodeError
from rest_framework import status, HTTP_HEADER_ENCODING
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken

from admin_cohort.models import User
from admin_cohort.settings import JWT_AUTH_MODE, OIDC_AUTH_MODE, JWT_ACCESS_COOKIE
from admin_cohort.types import PersonIdentity, ServerError, JwtTokens, LoginError, UserInfo, MissingDataError

env = environ.Env()

AUTH_SERVER_APP_HEADER = "X-User-App"
APP_NAME = env("JWT_APP_NAME")

JWT_SERVER_HEADERS = {AUTH_SERVER_APP_HEADER: APP_NAME}

ID_CHECKER_URL = env("ID_CHECKER_URL")
ID_CHECKER_TOKEN_HEADER = env("ID_CHECKER_TOKEN_HEADER")
ID_CHECKER_TOKEN = env("ID_CHECKER_TOKEN")
id_checker_server_headers = {ID_CHECKER_TOKEN_HEADER: ID_CHECKER_TOKEN}

JWT_SERVER_URL = env("JWT_SERVER_URL")
JWT_SERVER_TOKEN_URL = f"{JWT_SERVER_URL}/jwt/"
JWT_SERVER_REFRESH_URL = f"{JWT_SERVER_URL}/jwt/refresh/"
JWT_SERVER_USERINFO_URL = f"{JWT_SERVER_URL}/jwt/user_info/"
JWT_SIGNING_KEY = env("JWT_SIGNING_KEY")

JWT_ALGORITHMS = env("JWT_ALGORITHMS").split(',')

OIDC_SERVER_MASTER_URL = env("OIDC_SERVER_MASTER_URL")

OIDC_SERVER_APPLICATIFS_URL = env("OIDC_SERVER_APPLICATIFS_URL")
OIDC_SERVER_TOKEN_URL = f"{OIDC_SERVER_APPLICATIFS_URL}/protocol/openid-connect/token"
OIDC_SERVER_USERINFO_URL = f"{OIDC_SERVER_APPLICATIFS_URL}/protocol/openid-connect/userinfo"
OIDC_SERVER_LOGOUT_URL = f"{OIDC_SERVER_APPLICATIFS_URL}/protocol/openid-connect/logout"

OIDC_AUDIENCES = env("OIDC_AUDIENCES").split(';')
OIDC_CLIENT_ID = env("OIDC_CLIENT_ID")
OIDC_CLIENT_SECRET = env("OIDC_CLIENT_SECRET")
OIDC_GRANT_TYPE = env("OIDC_GRANT_TYPE")
OIDC_REDIRECT_URI = env("OIDC_REDIRECT_URI")

_logger = logging.getLogger('info')
_logger_err = logging.getLogger('django.request')


def get_jwt_tokens(username: str, password: str) -> JwtTokens:
    resp = requests.post(url=JWT_SERVER_TOKEN_URL,
                         data={"username": username,
                               "password": password},
                         headers=JWT_SERVER_HEADERS)
    if resp.status_code == status.HTTP_401_UNAUTHORIZED:
        raise LoginError("Invalid username or password")
    if resp.status_code != status.HTTP_200_OK:
        raise ServerError(f"Error {resp.status_code} from authentication server: {resp.text}")
    return JwtTokens(**resp.json())


def get_oidc_tokens(code):
    data = {"client_id": OIDC_CLIENT_ID,
            "client_secret": OIDC_CLIENT_SECRET,
            "redirect_uri": OIDC_REDIRECT_URI,
            "grant_type": OIDC_GRANT_TYPE,
            "code": code
            }
    response = requests.post(url=OIDC_SERVER_TOKEN_URL, data=data)
    response.raise_for_status()
    return JwtTokens(**response.json())


def get_oidc_user_info(access_token: str):
    return requests.get(url=OIDC_SERVER_USERINFO_URL,
                        headers={"Authorization": f"Bearer {access_token}"})


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
    auth_mode = request.META.get("HTTP_AUTHORIZATIONMETHOD")
    if auth_mode == JWT_AUTH_MODE:
        auth_logout(request)
    elif auth_mode == OIDC_AUTH_MODE:
        requests.post(url=OIDC_SERVER_LOGOUT_URL,
                      data={"client_id": OIDC_CLIENT_ID,
                            "client_secret": OIDC_CLIENT_SECRET,
                            "refresh_token": request.jwt_refresh_key},
                      headers={"Authorization": f"Bearer {request.jwt_access_key}"})
    else:
        _logger.warning(f"Unknown `AUTHORIZATIONMETHOD` header: {auth_mode}."
                        f"User: {request.user} ACCESS_TOKEN: {request.COOKIES.get('access')}")


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


def verify_oidc_token_for_issuer(token: str, issuer: str):
    try:
        return decode_oidc_token(token=token, issuer=issuer)
    except DecodeError as de:
        _logger_err.error(f"Error decoding token for issuer `{issuer}` - {de}")
        return None


def get_userinfo_from_token(token: str, auth_method: str) -> Union[None, UserInfo]:
    if token == env("ETL_TOKEN"):
        _logger.info("ETL token connexion")
        return UserInfo.solr()
    if token == env("SJS_TOKEN"):
        _logger.info("SJS token connexion")
        return UserInfo.sjs()

    if auth_method == JWT_AUTH_MODE:
        try:
            decoded = jwt.decode(token, key=JWT_SIGNING_KEY, algorithms=JWT_ALGORITHMS, leeway=15)
            user = User.objects.get(pk=decoded["username"])
            return UserInfo(username=user.provider_username,
                            firstname=user.firstname,
                            lastname=user.lastname,
                            email=user.email)
        except DecodeError as de:
            raise ServerError(f"Invalid JWT Token. Error decoding token - {de}")
        except User.DoesNotExist as e:
            raise ServerError(f"Error verifying token. User not found - {e}")
    elif auth_method == OIDC_AUTH_MODE:
        for issuer in (OIDC_SERVER_APPLICATIFS_URL, OIDC_SERVER_MASTER_URL):
            decoded = verify_oidc_token_for_issuer(token=token,
                                                   issuer=issuer)
            if decoded:
                return UserInfo(username=decoded['preferred_username'],
                                firstname=decoded['name'],
                                lastname=decoded['family_name'],
                                email=decoded['email'])
        raise InvalidToken("Invalid OIDC Token: unknown issuer")
    else:
        raise ValueError(f"Invalid authentication method : {auth_method}")


def get_auth_data(request) -> (str, str):
    raw_token, auth_method = get_token_from_headers(request)
    if not raw_token:
        raw_token = request.COOKIES.get(JWT_ACCESS_COOKIE)
    return raw_token, auth_method


def get_token_from_headers(request) -> (str, str):
    authorization_header = request.META.get('HTTP_AUTHORIZATION')
    authorization_method_header = request.META.get('HTTP_AUTHORIZATIONMETHOD')

    # Work around django test client oddness
    if isinstance(authorization_header, str):
        authorization_header = authorization_header.encode(HTTP_HEADER_ENCODING)
    if isinstance(authorization_method_header, str):
        authorization_method_header = authorization_method_header.encode(HTTP_HEADER_ENCODING)
    if authorization_header is None:
        return None, None
    return get_raw_token(authorization_header), authorization_method_header


def get_raw_token(header: bytes) -> Union[str, None]:
    from rest_framework_simplejwt.authentication import AUTH_HEADER_TYPE_BYTES

    parts = header.split()
    if len(parts) == 0:
        return None
    if parts[0] not in AUTH_HEADER_TYPE_BYTES:
        return None
    if len(parts) != 2:
        raise AuthenticationFailed('Authorization header must contain two space-delimited values',
                                   code='bad_authorization_header')
    res = parts[1]
    return res if not isinstance(res, bytes) else res.decode('utf-8')


def check_id_aph(id_aph: str) -> Optional[PersonIdentity]:
    resp = requests.post(url=ID_CHECKER_URL, data={'username': id_aph}, headers=id_checker_server_headers)
    if status.is_server_error(resp.status_code):
        raise ServerError(f"Error {resp.status_code} from id-checker server ({ID_CHECKER_URL}): {resp.text}")
    if resp.status_code != status.HTTP_200_OK:
        raise ServerError(f"Internal error: {resp.text}")

    res: dict = resp.json().get('data', {}).get('attributes', {})
    for expected in ['givenName', 'sn', 'sAMAccountName', 'mail']:
        if expected not in res:
            raise MissingDataError(f"JWT server response is missing {expected} ({resp.content})")
    return PersonIdentity(firstname=res.get('givenName'),
                          lastname=res.get('sn'),
                          user_id=res.get('sAMAccountName'),
                          email=res.get('mail'))
