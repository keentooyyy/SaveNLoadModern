from functools import wraps

from django.conf import settings
from django.utils import timezone
from rest_framework.response import Response

import jwt

from SaveNLoad.models import SimpleUsers
from SaveNLoad.utils.jwt_utils import decode_token
from SaveNLoad.services.redis_worker_service import get_user_workers


def login_required(view_func):
    """
    Custom login required decorator using JWT cookies - IDOR-proof
    
    Security features:
    - Uses get_current_user() for all validation logic (DRY principle)
    - Returns JSON error for unauthenticated requests
    - Attaches user to request.user for view access
    
    Note: All session validation, user_id validation, and database checks
    are handled by get_current_user() to avoid code duplication.

    Args:
        view_func: View function to wrap.

    Returns:
        Wrapped view function.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        """
        Enforce authentication and attach user to the request.

        Args:
            request: Django request object.
            *args: Positional arguments forwarded to the view.
            **kwargs: Keyword arguments forwarded to the view.

        Returns:
            HttpResponse from the wrapped view or redirect/JsonResponse on failure.
        """
        # Use get_current_user() to handle all validation logic
        user = get_current_user(request)

        if not user:
            return Response({'error': 'Not authenticated. Please log in.', 'requires_login': True}, status=401)

        # User is authenticated - attach to request and proceed
        request.user = user
        return view_func(request, *args, **kwargs)

    return wrapper


def client_worker_required(view_func):
    """
    Decorator to ensure client worker is connected before allowing access.
    Checks if the current user owns any active workers.

    Args:
        view_func: View function to wrap.

    Returns:
        Wrapped view function.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        """
        Enforce worker availability before proceeding.

        Args:
            request: Django request object.
            *args: Positional arguments forwarded to the view.
            **kwargs: Keyword arguments forwarded to the view.

        Returns:
            HttpResponse from the wrapped view or redirect/JsonResponse on failure.
        """
        # Check authentication first
        user = get_current_user(request)
        if not user:
            return Response({
                'error': 'Not authenticated. Please log in.',
                'requires_login': True
            }, status=401)

        # Check for active worker owned by this user
        # 6-second timeout matches is_online default
        # Check if user has any online workers
        worker_ids = get_user_workers(user.id)
        has_worker = len(worker_ids) > 0

        if not has_worker:
            return Response({
                'error': 'Client worker not connected. Please ensure the client worker is running and claimed.',
                'requires_worker': True
            }, status=503)

        return view_func(request, *args, **kwargs)

    return wrapper


def get_current_user(request):
    """
    Get current user from JWT - IDOR-proof implementation
    
    Security features:
    - Validates access token exists and is not expired
    - Validates user_id is a valid integer (prevents type confusion attacks)
    - Verifies user still exists in database (prevents deleted user access)
    - Fails closed for invalid tokens
    - Returns None if any validation fails (fail-secure)
    - Implements request-level caching to prevent multiple DB queries
    
    Args:
        request: Django request object
        
    Returns:
        SimpleUsers instance if valid, None otherwise
    """
    # Check cache first
    if hasattr(request, '_cached_user'):
        return request._cached_user

    token = None
    token_kind = 'access'

    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ', 1)[1].strip()

    if not token:
        token = request.COOKIES.get(settings.AUTH_ACCESS_COOKIE_NAME)

    if not token:
        return None

    try:
        payload = decode_token(token, token_kind)
        user_id = int(payload.get('sub', 0))
    except (jwt.InvalidTokenError, ValueError):
        return None

    # Validate user_id is a valid integer (prevent type confusion attacks)
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return None

    # Validate user_id is positive (prevent negative IDs or zero)
    if user_id <= 0:
        return None

    # Get user from database - verify it still exists
    try:
        user = SimpleUsers.objects.get(id=user_id)
        if getattr(user, 'is_guest', False) and user.guest_expires_at:
            if user.guest_expires_at <= timezone.now():
                try:
                    from SaveNLoad.utils.jwt_utils import revoke_all_refresh_tokens
                    revoke_all_refresh_tokens(user.id)
                except Exception:
                    pass
                return None
        # Update user's last authenticated request timestamp
        # This tracks actual authenticated requests to detect when cookies are cleared
        # More reliable than session data which can persist for days
        user.last_authenticated_request = timezone.now()
        user.save(update_fields=['last_authenticated_request'])
        # Cache for subsequent calls in same request
        request._cached_user = user
        return user
    except SimpleUsers.DoesNotExist:
        return None
    except Exception:
        # Unexpected error - fail securely
        return None
