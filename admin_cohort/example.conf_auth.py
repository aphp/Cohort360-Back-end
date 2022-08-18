from typing import Optional, Union

from rest_framework.request import Request


class LoginError(Exception):
    pass


class ServerError(Exception):
    pass


class IdResp:
    def __init__(self, firstname, lastname, user_id, email, **kwargs):
        self.firstname = firstname
        self.lastname = lastname
        self.user_id = user_id
        self.email = email

        for k, v in kwargs.items():
            setattr(self, k, v)


def check_id_aph(id_aph: str) -> Optional[IdResp]:
    raise NotImplementedError


class JwtTokens:
    def __init__(self, access: str, refresh: str, last_connection: dict = None,
                 **kwargs):
        self.access = access
        self.refresh = refresh
        self.last_connection = last_connection if last_connection else {}


def check_ids(username: str, password: str) -> JwtTokens:
    raise NotImplementedError


class UserInfo:
    def __init__(self, username: str, email: str,
                 firstname: str, lastname: str, **kwargs):
        self.username = username
        self.email = email
        self.firstname = firstname
        self.lastname = lastname


def get_user_info(jwt_access_token) -> UserInfo:
    raise NotImplementedError


def get_token_from_headers(request: Request) -> (str, str):
    """
    From request object (received in the authentication Middleware) retrieve
     authentication jwt token
    @param request:
    @return: tuple with jwt token and authentication method (can be null)
    if multiple auth methods are accepted
    """
    raise NotImplementedError


def verify_jwt(access_token: str, auth_method: str) -> Union[None, UserInfo]:
    raise NotImplementedError


def refresh_jwt(refresh: str) -> JwtTokens:
    raise NotImplementedError
