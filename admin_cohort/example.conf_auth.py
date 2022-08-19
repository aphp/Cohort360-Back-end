from typing import Optional, Union

from rest_framework.request import Request

from admin_cohort.types import UserInfo, IdResp, JwtTokens


def check_id_aph(id_aph: str) -> Optional[IdResp]:
    raise NotImplementedError


def check_ids(username: str, password: str) -> JwtTokens:
    raise NotImplementedError


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
