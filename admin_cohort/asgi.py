import os
from importlib import import_module

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path

from admin_cohort.settings import AUTH_MIDDLEWARE
from cohort.services.ws_event_manager import WebsocketManager

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin_cohort.settings')

asgi_application = get_asgi_application()

ws_auth_middleware = import_module(AUTH_MIDDLEWARE["module"])
WSAuthMiddlewareStack = getattr(ws_auth_middleware, AUTH_MIDDLEWARE["middleware"])

application = ProtocolTypeRouter({
    "http": asgi_application,
    "websocket": WSAuthMiddlewareStack(
        URLRouter([
            re_path(r'ws', WebsocketManager.as_asgi())
        ])
    )
})
