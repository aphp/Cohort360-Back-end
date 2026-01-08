import os
from importlib import import_module

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path
from django.conf import settings


WEBSOCKET_MANAGER = settings.WEBSOCKET_MANAGER

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin_cohort.settings')

asgi_application = get_asgi_application()

ws_manager_module = import_module(WEBSOCKET_MANAGER["module"])
WebsocketManager = getattr(ws_manager_module, WEBSOCKET_MANAGER["manager_class"])

application = ProtocolTypeRouter({
    "http": asgi_application,
    "websocket": URLRouter([re_path(r'ws', WebsocketManager.as_asgi())])
})
