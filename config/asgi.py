"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import SaveNLoad.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

http_application = get_asgi_application()

application = ProtocolTypeRouter({
    'http': http_application,
    'websocket': AuthMiddlewareStack(
        URLRouter(SaveNLoad.routing.websocket_urlpatterns)
    ),
})
