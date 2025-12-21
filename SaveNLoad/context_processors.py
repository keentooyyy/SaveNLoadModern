"""
Custom context processors for Django templates
"""
from django.conf import settings


def app_version(request):
    """
    Add application version to template context.
    
    If version couldn't be retrieved, will display error message.
    """
    return {
        'APP_VERSION': getattr(settings, 'APP_VERSION', "couldn't get version from online")
    }

