from asgiref.sync import sync_to_async
from channels.sessions import CookieMiddleware

from admin_cohort.services.auth import auth_service


@sync_to_async
def authenticate_ws_request(token, auth_method):
    return auth_service.authenticate_ws_request(token, auth_method)


class WSAuthMiddleware:

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if "user" not in scope:
            try:
                auth_method, token = scope.get('subprotocols')
            except ValueError:
                auth_method, token = None, None
            user = await authenticate_ws_request(token, auth_method)
            scope['user'] = user
        return await self.app(scope, receive, send)


# Shortcut to include cookie middleware
def WSAuthMiddlewareStack(app):
    return CookieMiddleware(WSAuthMiddleware(app))

