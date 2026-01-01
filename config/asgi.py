"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import SaveNLoad.routing

# Standard Django ASGI app for HTTP traffic.
http_application = get_asgi_application()

application = ProtocolTypeRouter({
    # Route HTTP requests to Django.
    'http': http_application,
    # Route WebSocket traffic to Channels with auth middleware.
    'websocket': AuthMiddlewareStack(
        URLRouter(SaveNLoad.routing.websocket_urlpatterns)
    ),
})
