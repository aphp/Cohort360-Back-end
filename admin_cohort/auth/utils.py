import logging
from typing import Optional, Union

import environ
import requests
from requests import HTTPError
from rest_framework import status, HTTP_HEADER_ENCODING
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken

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
JWT_SERVER_VERIFY_URL = f"{JWT_SERVER_URL}/jwt/verify/"
JWT_SERVER_USERINFO_URL = f"{JWT_SERVER_URL}/jwt/user_info/"
JWT_SIGNING_KEY = env("JWT_SIGNING_KEY")
JWT_ALGORITHM = env("JWT_ALGORITHM")

OIDC_SERVER_URL = env("OIDC_SERVER_URL")
OIDC_SERVER_TOKEN_URL = f"{OIDC_SERVER_URL}/protocol/openid-connect/token"
OIDC_SERVER_USERINFO_URL = f"{OIDC_SERVER_URL}/protocol/openid-connect/userinfo"
OIDC_SERVER_LOGOUT_URL = f"{OIDC_SERVER_URL}/protocol/openid-connect/logout"
OIDC_CERTS_URL = f"{OIDC_SERVER_URL}/protocol/openid-connect/certs"
OIDC_AUDIENCES = env("OIDC_AUDIENCES").split(';')
OIDC_SERVER_URL = env("OIDC_SERVER_URL")
OIDC_CLIENT_ID = env("OIDC_CLIENT_ID")
OIDC_CLIENT_SECRET = env("OIDC_CLIENT_SECRET")
OIDC_GRANT_TYPE = env("OIDC_GRANT_TYPE")
OIDC_REDIRECT_URI = env("OIDC_REDIRECT_URI")

JWT_AUTH_MODE = "jwt"
OIDC_AUTH_MODE = "oidc"

_logger = logging.getLogger('info')


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


def get_jwt_user_info(access_token: str):
    resp = requests.post(url=JWT_SERVER_USERINFO_URL,
                         data={"token": access_token},
                         headers=JWT_SERVER_HEADERS)
    resp.raise_for_status()
    return UserInfo(**resp.json())


def get_oidc_tokens(code):
    data = {"client_id": OIDC_CLIENT_ID,
            "client_secret": OIDC_CLIENT_SECRET,
            "redirect_uri": OIDC_REDIRECT_URI,
            "grant_type": OIDC_GRANT_TYPE,
            "code": code
            }
    response = requests.post(url=OIDC_SERVER_TOKEN_URL, data=data)
    response.raise_for_status()
    response = response.json()
    return JwtTokens(access=response.get("access_token"),
                     refresh=response.get("refresh_token"))


def get_oidc_user_info(access_token: str) -> Union[None, UserInfo]:
    response = requests.get(url=OIDC_SERVER_USERINFO_URL,
                            headers={"Authorization": f"Bearer {access_token}"})
    response.raise_for_status()
    return UserInfo.oidc(response.json())


def refresh_jwt_token(token: str):
    resp = requests.post(url=JWT_SERVER_REFRESH_URL,
                         data={"refresh": token},
                         headers=JWT_SERVER_HEADERS)
    resp.raise_for_status()
    return JwtTokens(**resp.json())


def refresh_oidc_token(token: str):
    resp = requests.post(url=OIDC_SERVER_TOKEN_URL,
                         data={"client_id": OIDC_CLIENT_ID,
                               "client_secret": OIDC_CLIENT_SECRET,
                               "grant_type": "refresh_token",
                               "refresh_token": token})
    resp.raise_for_status()
    resp = resp.json()
    return JwtTokens(access=resp.get("access_token"),
                     refresh=resp.get("refresh_token"))


def refresh_token(token: str):
    for refresher in (refresh_jwt_token, refresh_oidc_token):
        name = refresher.__name__
        try:
            return refresher(token)
        except HTTPError:
            continue
    raise InvalidToken()


def oidc_logout(request):
    response = requests.post(url=OIDC_SERVER_LOGOUT_URL,
                             data={"client_id": OIDC_CLIENT_ID,
                                   "client_secret": OIDC_CLIENT_SECRET,
                                   "refresh_token": request.jwt_refresh_key},
                             headers={"Authorization": f"Bearer {request.jwt_access_key}"})
    response.raise_for_status()


def verify_token(access_token: str) -> Union[None, UserInfo]:
    if access_token == env("ETL_TOKEN"):
        _logger.info("ETL token connexion")
        return UserInfo.solr()
    if access_token == env("SJS_TOKEN"):
        _logger.info("SJS token connexion")
        return UserInfo.sjs()

    for userinfo_verifier in (get_jwt_user_info, get_oidc_user_info):
        try:
            user_info = userinfo_verifier(access_token)
            return user_info
        except HTTPError:
            continue
    raise InvalidToken()


def get_raw_token(header: bytes) -> Union[str, None]:
    """
    Extracts an unvalidated JSON web token from the given "Authorization"
    header value.
    """
    from rest_framework_simplejwt.authentication import AUTH_HEADER_TYPE_BYTES

    parts = header.split()
    if len(parts) == 0:
        # Empty AUTHORIZATION header sent
        return None
    if parts[0] not in AUTH_HEADER_TYPE_BYTES:
        # Assume the header does not contain a JSON web token
        return None
    if len(parts) != 2:
        raise AuthenticationFailed('Authorization header must contain two space-delimited values',
                                   code='bad_authorization_header')
    res = parts[1]
    return res if not isinstance(res, bytes) else res.decode('utf-8')


def get_token_from_headers(request) -> (str, str):
    """
    Extracts the header containing the JSON web token from the given
    request.
    """
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
