from django.shortcuts import redirect, render
from django.urls import reverse
from django.http import JsonResponse
from functools import wraps
from SaveNLoad.models import SimpleUsers
from SaveNLoad.models.client_worker import ClientWorker


def login_required(view_func):
    """
    Custom login required decorator using sessions - IDOR-proof
    
    Security features:
    - Uses get_current_user() for all validation logic (DRY principle)
    - Returns JSON error for AJAX requests instead of redirecting
    - Attaches user to request.user for view access
    
    Note: All session validation, user_id validation, and database checks
    are handled by get_current_user() to avoid code duplication.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if this is an AJAX request
        # Check multiple indicators to reliably detect AJAX requests
        is_ajax = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
            request.META.get('HTTP_CONTENT_TYPE', '').startswith('application/json') or
            request.META.get('HTTP_ACCEPT', '').startswith('application/json') or
            request.path.startswith('/api/')
        )
        
        # Use get_current_user() to handle all validation logic
        user = get_current_user(request)
        
        if not user:
            # User not authenticated - return appropriate response
            if is_ajax:
                return JsonResponse({'error': 'Not authenticated. Please log in.', 'requires_login': True}, status=401)
            return redirect(reverse('SaveNLoad:login'))
        
        # User is authenticated - attach to request and proceed
        request.user = user
        return view_func(request, *args, **kwargs)
    return wrapper


def client_worker_required(view_func):
    """
    Decorator to ensure client worker is connected before allowing access.
    Checks session for client_id and validates worker is online (6s timeout).
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Check authentication first
        user = get_current_user(request)
        if not user:
            if is_ajax:
                return JsonResponse({
                    'error': 'Not authenticated. Please log in.',
                    'requires_login': True
                }, status=401)
            return redirect(reverse('SaveNLoad:login'))
        
        # Get client_id from URL (reconnection) or session
        worker = None
        if hasattr(request, 'session'):
            # Check URL first (for reconnection scenarios)
            client_id_from_url = request.GET.get('client_id', '').strip()
            if client_id_from_url:
                worker = ClientWorker.get_worker_by_id(client_id_from_url)
                if worker and worker.is_online():
                    # Associate URL worker with session
                    request.session['client_id'] = client_id_from_url
                    request.session.modified = True
            
            # If no URL worker, check session
            if not worker:
                client_id = request.session.get('client_id')
                if client_id:
                    worker = ClientWorker.get_worker_by_id(client_id)
                    # Clear stale client_id if worker is offline
                    if not worker or not worker.is_online():
                        request.session.pop('client_id', None)
                        request.session.modified = True
                        worker = None
        
        # Require valid online worker
        if not worker:
            if is_ajax:
                return JsonResponse({
                    'error': 'Client worker not connected. Please ensure the client worker is running on your machine.',
                    'requires_worker': True
                }, status=503)
            return render(request, 'SaveNLoad/worker_required.html')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def worker_required_unauthenticated(view_func):
    """
    Decorator for unauthenticated pages (login/register) that requires an active worker.
    - If user is already authenticated: allow access (view will redirect them)
    - If user is NOT authenticated: check for worker, show worker_required if none
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # First check if user is already authenticated
        user = get_current_user(request)
        if user:
            # User is authenticated - let them through
            # The view's redirect_if_logged_in() will handle redirecting them
            return view_func(request, *args, **kwargs)
        
        # User is NOT authenticated - check for worker
        # Check if client_id is in URL
        client_id_from_url = request.GET.get('client_id', '').strip()
        
        if client_id_from_url:
            # Validate specific worker from URL
            worker = ClientWorker.get_worker_by_id(client_id_from_url)
            if worker and worker.is_online():
                # Worker is online - allow access
                return view_func(request, *args, **kwargs)
        else:
            # No client_id in URL - check if ANY worker is online
            if ClientWorker.is_worker_connected():
                # At least one worker is online - allow access
                return view_func(request, *args, **kwargs)
        
        # No worker online - show worker required page
        return render(request, 'SaveNLoad/worker_required.html')
    
    return wrapper


def get_current_user(request):
    """
    Get current user from session - IDOR-proof implementation
    
    Security features:
    - Validates session exists and is not expired
    - Validates user_id is a valid integer (prevents type confusion attacks)
    - Verifies user still exists in database (prevents deleted user access)
    - Clears invalid sessions automatically
    - Returns None if any validation fails (fail-secure)
    
    Args:
        request: Django request object
        
    Returns:
        SimpleUsers instance if valid, None otherwise
    """
    # Check if session exists
    if not hasattr(request, 'session'):
        return None
    
    # Get user_id from session
    user_id = request.session.get('user_id')
    
    if not user_id:
        return None
    
    # Validate user_id is a valid integer (prevent type confusion attacks)
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        # Invalid user_id type - clear session and return None
        request.session.flush()
        return None
    
    # Validate user_id is positive (prevent negative IDs or zero)
    if user_id <= 0:
        request.session.flush()
        return None
    
    # Get user from database - verify it still exists
    try:
        user = SimpleUsers.objects.get(id=user_id)
        return user
    except SimpleUsers.DoesNotExist:
        # User was deleted - clear session to prevent orphaned sessions
        request.session.flush()
        return None
    except Exception:
        # Unexpected error - fail securely
        return None
