import logging
import os
from json import JSONDecodeError
from typing import Optional

import requests

from rest_framework import status
from rest_framework.exceptions import APIException

env = os.environ

IDENTITY_SERVER_URL = env.get("IDENTITY_SERVER_URL", "")
IDENTITY_SERVER_AUTH_ENDPOINT = f"{IDENTITY_SERVER_URL}/user/authenticate"
IDENTITY_SERVER_USER_INFO_ENDPOINT = f"{IDENTITY_SERVER_URL}/user/info"
IDENTITY_SERVER_HEADERS = {"Key-auth": env.get("IDENTITY_SERVER_AUTH_TOKEN", "")}

_logger = logging.getLogger('django.request')


def authenticate_user(username: str, password: str) -> Optional[bool]:
    try:
        response = requests.post(url=IDENTITY_SERVER_AUTH_ENDPOINT,
                                 data={"username": username, "password": password},
                                 headers=IDENTITY_SERVER_HEADERS
                                 )
        return response.status_code == status.HTTP_200_OK
    except Exception as e:
        _logger.error(f"[Identity Server] Error authenticating user `{username}`: {e}")
        raise APIException()


def check_user_identity(username: str) -> Optional[dict]:
    response = requests.post(url=IDENTITY_SERVER_USER_INFO_ENDPOINT,
                             data={'username': username},
                             headers=IDENTITY_SERVER_HEADERS)
    if response.status_code == status.HTTP_200_OK:
        try:
            user_attrs = response.json().get('data', {}).get('attributes', {})
            return dict(firstname=user_attrs['givenName'],
                        lastname=user_attrs['sn'],
                        username=user_attrs['cn'],
                        email=user_attrs['mail'])
        except JSONDecodeError:
            raise APIException(f"[Identity Server] Invalid response: {response.text}")
        except KeyError as ke:
            raise APIException(f"[Identity Server] Missing field in response: {ke}")
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        return None
    else:
        raise APIException(f"[Identity Server] Error: {response.status_code}-{response.text}")
