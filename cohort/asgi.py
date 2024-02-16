import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path

from cohort.services import ws_event_manager

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin_cohort.settings')


websocket_urlpatterns = [
    re_path(r'ws', ws_event_manager.WebsocketManager.as_asgi()),
]

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter(websocket_urlpatterns),
})
