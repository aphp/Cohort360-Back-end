from channels.db import database_sync_to_async
from channels.sessions import CookieMiddleware

from admin_cohort.models import User
from admin_cohort.services.auth import auth_service


@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None


class WSAuthMiddleware:

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        print("************* scope", scope)     # scope["query_string"]
        if "user" not in scope:
            token, auth_method = scope['token'], scope['auth_method']
            user_id = auth_service.authenticate_ws_request(token, auth_method)  # maybe will need to use a sync_to_async decorated version for auth
            scope['user'] = await get_user(user_id)
        return await self.app(scope, receive, send)


# Shortcut to include cookie middleware
def WSAuthMiddlewareStack(app):
    return CookieMiddleware(WSAuthMiddleware(app))

# todo: try and put this version as final solution
# class WSAuthMiddlewareStack:
#
#     async def __call__(self, app, *args, **kwargs):
#         return CookieMiddleware(WSAuthMiddleware(app))
