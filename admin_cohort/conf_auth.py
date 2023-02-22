import json
import logging
from typing import Optional, Union

import environ
import jwt
import requests
from django.utils import timezone
from rest_framework import status, HTTP_HEADER_ENCODING
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from admin_cohort.settings import SERVER_VERSION
from admin_cohort.types import PersonIdentity, ServerError, JwtTokens, LoginError, UserInfo, MissingDataError

env = environ.Env()

AUTH_SERVER_APP_HEADER = "X-User-App"
APP_NAME = env("JWT_APP_NAME")

jwt_server_headers = {AUTH_SERVER_APP_HEADER: APP_NAME}

ID_CHECKER_URL = env("ID_CHECKER_URL")
ID_CHECKER_TOKEN_HEADER = env("ID_CHECKER_TOKEN_HEADER")
ID_CHECKER_TOKEN = env("ID_CHECKER_TOKEN")
id_checker_server_headers = {ID_CHECKER_TOKEN_HEADER: ID_CHECKER_TOKEN}

JWT_SERVER_URL = env("JWT_SERVER_URL")
JWT_SIGNING_KEY = env("JWT_SIGNING_KEY")
JWT_ALGORITHM = env("JWT_ALGORITHM")

OIDC_SERVER_URL = env("OIDC_SERVER_URL")
OIDC_CERTS_URL = f"{OIDC_SERVER_URL}/protocol/openid-connect/certs"
OIDC_AUDIENCES = env("OIDC_AUDIENCES").split(';')

JWT_AUTH_MODE = "jwt"
OIDC_AUTH_MODE = "oidc"
_logger = logging.getLogger('info')


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
    header_authorization = request.META.get('HTTP_AUTHORIZATION')
    header_authorization_method = request.META.get('HTTP_AUTHORIZATIONMETHOD')

    # Work around django test client oddness
    if isinstance(header_authorization, str):
        header_authorization = header_authorization.encode(HTTP_HEADER_ENCODING)
    if isinstance(header_authorization_method, str):
        header_authorization_method = header_authorization_method.encode(HTTP_HEADER_ENCODING)
    if header_authorization is None:
        return None, None
    return get_raw_token(header_authorization), header_authorization_method


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


def check_ids(username: str, password: str) -> JwtTokens:
    if SERVER_VERSION.lower() == "dev":
        return JwtTokens(username, username, {"created_at": timezone.now() - timezone.timedelta(days=1),
                                              "modified_at": timezone.now() - timezone.timedelta(days=1),
                                              "app_name": 'localhost'
                                              })

    resp = requests.post(url=f"{JWT_SERVER_URL}/jwt/",
                         data={"username": username, "password": password},
                         headers=jwt_server_headers)
    if resp.status_code == status.HTTP_401_UNAUTHORIZED:
        raise LoginError("Invalid username or password")
    if resp.status_code != 200:
        raise ServerError(f"Error {resp.status_code} from authentication server: {resp.text}")
    return JwtTokens(**resp.json())


def get_user_info(jwt_access_token: str) -> UserInfo:
    if SERVER_VERSION.lower() == "dev":
        from admin_cohort.models import User
        u: User = User.objects.get(pk=jwt_access_token)
        return UserInfo(u.provider_username, u.email, u.firstname, u.lastname)

    resp = requests.post(url="{}/jwt/user_info/".format(JWT_SERVER_URL),
                         data={"token": jwt_access_token},
                         headers=jwt_server_headers)
    if resp.status_code == 200:
        return UserInfo(**resp.json())
    raise ValueError("Invalid JWT Access Token")


def verify_jwt(access_token: str, auth_method: str = JWT_AUTH_MODE) -> Union[None, UserInfo]:
    if SERVER_VERSION.lower() == "dev":
        return
    if access_token == env("ETL_TOKEN"):
        _logger.info("*** ETL TOKEN CONNEXION *** ")
        return UserInfo(username="SOLR_ETL",
                        email="solr.etl@aphp.fr",
                        firstname="Solr",
                        lastname="ETL")
    if access_token == env("SJS_TOKEN"):
        _logger.info("*** SJS TOKEN CONNEXION *** ")
        return UserInfo(username="SPARK_JOB_SERVER",
                        email="spark.jobserver@aphp.fr",
                        firstname="SparkJob",
                        lastname="SERVER")
    auth_method = auth_method or JWT_AUTH_MODE
    if auth_method.lower() == JWT_AUTH_MODE:
        url = f"{JWT_SERVER_URL}/jwt/verify/"
        resp = requests.post(url=url,
                             data={"token": access_token},
                             headers=jwt_server_headers)

        if resp.status_code == status.HTTP_200_OK:
            jwt.decode(access_token, leeway=15, algorithms=JWT_ALGORITHM, options=dict(verify_signature=False,
                                                                                       verify_exp=True))
            return get_user_info(access_token)
        elif status.is_server_error(resp.status_code):
            raise ServerError(f"Error {resp.status_code} from authentication server ({url}): {resp.text}")
        raise ValueError("Invalid JWT Access Token")
    elif auth_method.lower() == OIDC_AUTH_MODE:
        resp = requests.get(OIDC_CERTS_URL)
        if resp.status_code != status.HTTP_200_OK:
            raise ServerError(f"Error {resp.status_code} from authentication server ({OIDC_CERTS_URL}): {resp.text}")
        jwks = resp.json()
        public_keys = {}
        for jwk in jwks['keys']:
            kid = jwk['kid']
            public_keys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))

        kid = jwt.get_unverified_header(access_token)['kid']
        key = public_keys[kid]
        decoded = jwt.decode(jwt=access_token,
                             key=key,
                             verify=True,
                             algorithms=['RS256'],
                             issuer=OIDC_SERVER_URL,
                             audience=OIDC_AUDIENCES)
        return UserInfo(username=decoded['preferred_username'],
                        lastname=decoded['family_name'],
                        firstname=decoded['name'],
                        key=key)
    else:
        raise ValueError(f"Invalid authentication method: {auth_method}")


def refresh_jwt(refresh) -> JwtTokens:
    if SERVER_VERSION.lower() == "dev":
        return JwtTokens(refresh, refresh)

    resp = requests.post(url="{}/jwt/refresh/".format(JWT_SERVER_URL),
                         data=dict(refresh=refresh),
                         headers=jwt_server_headers)
    if resp.status_code == 200:
        return JwtTokens(**resp.json())
    raise ValueError("Invalid JWT Refresh Token")
