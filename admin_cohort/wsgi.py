"""
WSGI config for admin_cohort project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.wsgi import get_wsgi_application

from admin_cohort import websocket_consumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin_cohort.settings')

# application = get_wsgi_application()

application = ProtocolTypeRouter(
    {
        "http": get_wsgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(
                websocket_consumer
            )
        ),
    }
)
