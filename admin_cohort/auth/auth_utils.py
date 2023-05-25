import json
import logging
from typing import Optional, Union

import environ
import jwt
import requests
from django.utils import timezone
from rest_framework import status, HTTP_HEADER_ENCODING
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from admin_cohort.models import User
from admin_cohort.settings import SERVER_VERSION
from admin_cohort.types import PersonIdentity, ServerError, JwtTokens, LoginError, UserInfo, MissingDataError

env = environ.Env()

AUTH_SERVER_APP_HEADER = "X-User-App"
APP_NAME = env("JWT_APP_NAME")

JWT_SERVER_HEADERS = {AUTH_SERVER_APP_HEADER: APP_NAME}

ID_CHECKER_URL = env("ID_CHECKER_URL")
ID_CHECKER_TOKEN_HEADER = env("ID_CHECKER_TOKEN_HEADER")
ID_CHECKER_TOKEN = env("ID_CHECKER_TOKEN")
id_checker_server_headers = {ID_CHECKER_TOKEN_HEADER: ID_CHECKER_TOKEN}

JWT_SERVER_URL = f"{env('JWT_SERVER_URL')}/jwt"
JWT_SERVER_REFRESH_URL = f"{JWT_SERVER_URL}/jwt/refresh/"
JWT_SERVER_VERIFY_URL = f"{JWT_SERVER_URL}/verify/"
JWT_SERVER_USERINFO_URL = f"{JWT_SERVER_URL}/user_info/"
JWT_SIGNING_KEY = env("JWT_SIGNING_KEY")
JWT_ALGORITHM = env("JWT_ALGORITHM")

OIDC_SERVER_URL = env("OIDC_SERVER_URL")
OIDC_SERVER_TOKEN_URL = f"{OIDC_SERVER_URL}/protocol/openid-connect/token"
OIDC_SERVER_USERINFO_URL = f"{OIDC_SERVER_URL}/protocol/openid-connect/userinfo"
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


def get_jwt_tokens(username: str, password: str) -> JwtTokens:
    if SERVER_VERSION.lower() == "dev":
        return JwtTokens(username, username, {"created_at": timezone.now() - timezone.timedelta(days=1),
                                              "modified_at": timezone.now() - timezone.timedelta(days=1),
                                              "app_name": 'localhost'
                                              })

    resp = requests.post(url=JWT_SERVER_URL,
                         data={"username": username, "password": password},
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
    response = response.json()
    user_info = get_oidc_user_info(access_token=response["access_token"])
    user = User.objects.get(provider_username=user_info.username)
    return user, response["access_token"], response["refresh_token"]


def get_oidc_user_info(access_token: str) -> Union[None, UserInfo]:
    response = requests.get(url=OIDC_SERVER_USERINFO_URL,
                            headers={"Authorization": f"Bearer {access_token}"})
    if response.status_code != status.HTTP_200_OK:
        raise ServerError(f"Error {response.status_code} from OIDC provider: {response.text}")
    response = response.json()
    return UserInfo(username=response.get('preferred_username'),
                    firstname=response.get('given_name'),
                    lastname=response.get('family_name'),
                    email=response.get('email'))


def get_user_info(jwt_access_token: str) -> UserInfo:
    if SERVER_VERSION.lower() == "dev":
        from admin_cohort.models import User
        u: User = User.objects.get(pk=jwt_access_token)
        return UserInfo(u.provider_username, u.email, u.firstname, u.lastname)

    resp = requests.post(url=JWT_SERVER_USERINFO_URL, data={"token": jwt_access_token}, headers=JWT_SERVER_HEADERS)
    if resp.status_code == 200:
        return UserInfo(**resp.json())
    raise ValueError("Invalid JWT Access Token")


def verify_token(access_token: str, auth_method: str = None) -> Union[None, UserInfo]:
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
        resp = requests.post(url=JWT_SERVER_VERIFY_URL, data={"token": access_token}, headers=JWT_SERVER_HEADERS)
        resp.raise_for_status()
        if resp.status_code == status.HTTP_200_OK:
            jwt.decode(jwt=access_token,
                       leeway=15,
                       algorithms=JWT_ALGORITHM,
                       options=dict(verify_signature=False, verify_exp=True))
            return get_user_info(access_token)
    elif auth_method.lower() == OIDC_AUTH_MODE:
        resp = requests.get(url=OIDC_CERTS_URL)
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

    resp = requests.post(url=JWT_SERVER_REFRESH_URL,
                         data=dict(refresh=refresh),
                         headers=JWT_SERVER_HEADERS)
    if resp.status_code == 200:
        return JwtTokens(**resp.json())
    raise ValueError("Invalid JWT Refresh Token")
