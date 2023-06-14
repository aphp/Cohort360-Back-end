import json
import logging
from collections import defaultdict
from typing import Optional, Union

import environ
import jwt
import requests
from django.contrib.auth import logout as auth_logout
from jwt import DecodeError
from requests import RequestException
from rest_framework import status, HTTP_HEADER_ENCODING
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken

from admin_cohort.models import User
from admin_cohort.types import PersonIdentity, ServerError, JwtTokens, LoginError, UserInfo, MissingDataError, TokenVerificationError

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

OIDC_SERVER_URL = env("OIDC_SERVER_URL")
OIDC_SERVER_TOKEN_URL = f"{OIDC_SERVER_URL}/protocol/openid-connect/token"
OIDC_SERVER_USERINFO_URL = f"{OIDC_SERVER_URL}/protocol/openid-connect/userinfo"
OIDC_SERVER_LOGOUT_URL = f"{OIDC_SERVER_URL}/protocol/openid-connect/logout"
OIDC_SERVER_CERTS_URL = f"{OIDC_SERVER_URL}/protocol/openid-connect/certs"
OIDC_AUDIENCES = env("OIDC_AUDIENCES").split(';')
OIDC_SERVER_URL = env("OIDC_SERVER_URL")
OIDC_CLIENT_ID = env("OIDC_CLIENT_ID")
OIDC_CLIENT_SECRET = env("OIDC_CLIENT_SECRET")
OIDC_GRANT_TYPE = env("OIDC_GRANT_TYPE")
OIDC_REDIRECT_URI = env("OIDC_REDIRECT_URI")

OIDC_SERVER_APPLICATIFS_URL = OIDC_SERVER_URL.replace("master", "ID-Applicatifs")
OIDC_SERVER_APPLICATIFS_CERTS_URL = f"{OIDC_SERVER_APPLICATIFS_URL}/protocol/openid-connect/certs"

JWT_AUTH_MODE = "JWT"
OIDC_AUTH_MODE = "OIDC"

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


def get_jwt_user_info(access_token: str):
    return requests.post(url=JWT_SERVER_USERINFO_URL,
                         data={"token": access_token},
                         headers=JWT_SERVER_HEADERS)


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


def oidc_logout(request):
    response = requests.post(url=OIDC_SERVER_LOGOUT_URL,
                             data={"client_id": OIDC_CLIENT_ID,
                                   "client_secret": OIDC_CLIENT_SECRET,
                                   "refresh_token": request.jwt_refresh_key},
                             headers={"Authorization": f"Bearer {request.jwt_access_key}"})
    response.raise_for_status()


def logout_user(request):
    auth_logout(request)
    try:
        oidc_logout(request)
    except RequestException as e:
        _logger_err.error(f"Error logging user out from OIDC provider - {e}")


def verify_token(access_token: str) -> Union[None, UserInfo]:
    if access_token == env("ETL_TOKEN"):
        _logger.info("ETL token connexion")
        return UserInfo.solr()
    if access_token == env("SJS_TOKEN"):
        _logger.info("SJS token connexion")
        return UserInfo.sjs()

    errors = defaultdict(list)
    for userinfo_verifier in (get_jwt_user_info, get_oidc_user_info):
        try:
            response = userinfo_verifier(access_token)
            if response.status_code == status.HTTP_200_OK:
                return UserInfo(**response.json())
            elif response.status_code == status.HTTP_401_UNAUTHORIZED:
                raise InvalidToken()
            response.raise_for_status()
        except (InvalidToken, RequestException) as e:
            errors[userinfo_verifier.__name__].append(e)
    if errors:
        _logger_err.error(f"Error while verifying access token: {errors}")
        raise TokenVerificationError()


def decode_oidc_token(access_token: str, oidc_server_url: str, oidc_certs_url: str):
    resp = requests.get(url=oidc_certs_url)
    if resp.status_code != status.HTTP_200_OK:
        raise ServerError(f"Error {resp.status_code} from OIDC Auth Server ({oidc_certs_url}): {resp.text}")
    jwks = resp.json()
    public_keys = {}
    for jwk in jwks['keys']:
        kid = jwk['kid']
        public_keys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))

    kid = jwt.get_unverified_header(access_token)['kid']
    key = public_keys[kid]
    return jwt.decode(jwt=access_token,
                      key=key,
                      verify=True,
                      algorithms=JWT_ALGORITHMS,
                      issuer=oidc_server_url,
                      audience=OIDC_AUDIENCES)


def verify_oidc_token_from_realm_applicatifs(access_token: str):
    decoded = decode_oidc_token(access_token=access_token,
                                oidc_server_url=OIDC_SERVER_APPLICATIFS_URL,
                                oidc_certs_url=OIDC_SERVER_APPLICATIFS_CERTS_URL)
    print(f"{decoded=}")
    return UserInfo(username=decoded['preferred_username'],
                    lastname=decoded['family_name'],
                    firstname=decoded['name'],                  # /!\ check if it is 'name' or 'given_name'
                    # email=decoded['email'],                   # /!\ check if 'email' exists
                    )


def verify_oidc_token_from_realm_master(access_token: str):
    decoded = decode_oidc_token(access_token=access_token,
                                oidc_server_url=OIDC_SERVER_URL,
                                oidc_certs_url=OIDC_SERVER_CERTS_URL)
    print(f"{decoded=}")
    return UserInfo(username=decoded['preferred_username'],
                    lastname=decoded['family_name'],
                    firstname=decoded['name'],                  # /!\ check if it is 'name' or 'given_name'
                    # email=decoded['email'],                   # /!\ check if 'email' exists
                    )


def verify_token_2(access_token: str, auth_method: str = JWT_AUTH_MODE) -> Union[None, UserInfo]:
    if access_token == env("ETL_TOKEN"):
        _logger.info("ETL token connexion")
        return UserInfo.solr()
    if access_token == env("SJS_TOKEN"):
        _logger.info("SJS token connexion")
        return UserInfo.sjs()

    if auth_method == JWT_AUTH_MODE:
        try:
            decoded = jwt.decode(access_token, leeway=15, algorithms=JWT_ALGORITHMS, options={"verify_signature": False})
            user = User.objects.get(pk=decoded["username"])
            return UserInfo(**user.__dict__)
        except DecodeError as de:
            raise ServerError(f"Invalid JWT Token. Error decoding token - {de}")
        except User.DoesNotExist as e:
            raise ServerError(f"Error verifying token. User not found - {e}")
    elif auth_method == OIDC_AUTH_MODE:
        try:
            decoded = jwt.decode(access_token, leeway=15, algorithms=["RS256", "HS256"], verify=True)
        except DecodeError as de:
            raise ServerError(f"Invalid OIDC Token. Error decoding token - {de}")

        if decoded["iss"] == OIDC_SERVER_APPLICATIFS_URL:
            return verify_oidc_token_from_realm_applicatifs(access_token)
        elif decoded["iss"] == OIDC_SERVER_URL:
            return verify_oidc_token_from_realm_master(access_token)
        else:
            raise ServerError("Invalid OIDC Token: unknown issuer")
    else:
        raise ValueError(f"Invalid authentication method : {auth_method}")


"""
    back    --- jwt --->     front   --- jwt --->     fhir   --- jwt --->    back   --- jwt --->   JWT_Server/verify

    back    --- oidc --->    front   --- oidc --->    fhir   --- oidc --->   back   --- oidc ---> jwt.decode(HS256,
                                                                                                             iss=/realms/master,
                                                                                                             aud=fhir-dev;portal-dev)

    portail_patient   --- oidc --->     fhir    --- oidc --->   back  ;------>   OIDC_Server/certs
                                                                       \----->   then:  jwt.decode(RS256,
                                                                                                   iss=/realms/master,
                                                                                                   aud=fhir-dev;portal-dev)
"""


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
