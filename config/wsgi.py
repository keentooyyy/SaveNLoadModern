"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application
from django.conf import settings
from whitenoise import WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_app = get_wsgi_application()

# Configure WhiteNoise to serve static and media files (LAN deployment)
# WhiteNoise middleware handles static files, this wrapper adds media files
application = WhiteNoise(django_app, root=str(settings.MEDIA_ROOT))
application.add_files(str(settings.MEDIA_ROOT), prefix=settings.MEDIA_URL)

