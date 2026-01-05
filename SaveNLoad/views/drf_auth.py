from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import BasePermission

from SaveNLoad.views.custom_decorators import get_current_user


class JwtCookieAuthentication(BaseAuthentication):
    """
    DRF authentication adapter for existing JWT logic.
    """

    def authenticate(self, request):
        user = get_current_user(request)
        if not user:
            return None
        return (user, None)


class IsAdminUserSimple(BasePermission):
    """
    Permission for SimpleUsers admin role.
    """

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and getattr(user, "is_admin", lambda: False)())
