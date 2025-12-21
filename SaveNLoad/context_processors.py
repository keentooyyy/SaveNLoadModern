"""
Custom context processors for Django templates
"""
from django.conf import settings


def app_version(request):
    """Add application version to template context"""
    return {
        'APP_VERSION': getattr(settings, 'APP_VERSION', '1.0.0')
    }

