from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from admin_cohort import websocket_consumer

application = ProtocolTypeRouter(
    {
        "websocket": AuthMiddlewareStack(
            URLRouter(
                [
                    path("ws/", websocket_consumer.WebSocketStatusConsumer.as_asgi()),
                ]
            )
        ),
    }
)
