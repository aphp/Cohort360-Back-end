from typing import Tuple

from asgiref.sync import sync_to_async
from channels.sessions import CookieMiddleware

from admin_cohort.services.auth import auth_service


@sync_to_async
def authenticate_ws_request(token, auth_method):
    return auth_service.authenticate_ws_request(token, auth_method)


class WSAuthMiddleware:
    AUTH_HEADER = "authorization"
    AUTH_METHOD_HEADER = "authorizationmethod"

    def __init__(self, app):
        self.app = app

    def _get_auth_data(self, scope: dict) -> Tuple[str, str]:
        headers = dict((k.decode('utf-8'), v.decode('utf-8')) for k, v in scope.get("headers"))
        token = headers[self.AUTH_HEADER]
        auth_method = headers[self.AUTH_METHOD_HEADER]
        return token, auth_method

    async def __call__(self, scope, receive, send):
        if "user" not in scope:
            user = await authenticate_ws_request(*self._get_auth_data(scope=scope))
            scope['user'] = user
        return await self.app(scope, receive, send)


# Shortcut to include cookie middleware
def WSAuthMiddlewareStack(app):
    return CookieMiddleware(WSAuthMiddleware(app))

