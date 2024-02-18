import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path

from cohort.services.ws_event_manager import WebsocketManager
from admin_cohort.middleware.ws_auth_middleware import WSAuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin_cohort.settings')

asgi_application = get_asgi_application()


# todo: use middleware for auth ?
#       https://channels.readthedocs.io/en/stable/deploying.html#configuring-the-asgi-application

websocket_urlpatterns = [
    re_path(r'ws', WebsocketManager.as_asgi()),
]

application = ProtocolTypeRouter({
    "http": asgi_application,
    "websocket": WSAuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
