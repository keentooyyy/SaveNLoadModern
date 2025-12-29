from django.shortcuts import redirect, render
from django.urls import reverse
from django.http import JsonResponse
from functools import wraps
from SaveNLoad.models import SimpleUsers
from SaveNLoad.services.redis_worker_service import get_user_workers, get_unclaimed_workers, is_worker_online


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
    Checks if the current user owns any active workers.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                  request.META.get('HTTP_CONTENT_TYPE', '').startswith('application/json')
        
        # Check authentication first
        user = get_current_user(request)
        if not user:
            if is_ajax:
                return JsonResponse({
                    'error': 'Not authenticated. Please log in.',
                    'requires_login': True
                }, status=401)
            return redirect(reverse('SaveNLoad:login'))
        
        # Check for active worker owned by this user
        # 6-second timeout matches is_online default
        from django.utils import timezone
        # Check if user has any online workers
        worker_ids = get_user_workers(user.id)
        has_worker = len(worker_ids) > 0
        
        if not has_worker:
            # Auto-claim first available unclaimed worker
            unpaired_worker_ids = get_unclaimed_workers()
            if unpaired_worker_ids:
                # Auto-claim the first available worker
                from SaveNLoad.services.redis_worker_service import claim_worker
                client_id = unpaired_worker_ids[0]
                if claim_worker(client_id, user.id):
                    print(f"Auto-claimed worker {client_id} to user {user.username}")
                    # Re-check for workers after auto-claim
                    worker_ids = get_user_workers(user.id)
                    has_worker = len(worker_ids) > 0
            
            if not has_worker:
                if is_ajax:
                    return JsonResponse({
                        'error': 'Client worker not connected. Please ensure the client worker is running and claimed.',
                        'requires_worker': True
                    }, status=503)
                
                # Fetch all online workers to show in the UI
                from SaveNLoad.services.redis_worker_service import get_online_workers, get_worker_info
                online_worker_ids = get_online_workers()
                online_workers = []
                for wid in online_worker_ids:
                    worker_info = get_worker_info(wid)
                    user_id = worker_info.get('user_id') if worker_info else None
                    linked_username = None
                    if user_id:
                        try:
                            linked_user = SimpleUsers.objects.get(pk=user_id)
                            linked_username = linked_user.username
                        except SimpleUsers.DoesNotExist:
                            pass
                    online_workers.append({
                        'client_id': wid,
                        'linked_user': linked_username,
                        'claimed': user_id is not None
                    })
                
                return render(request, 'SaveNLoad/worker_required.html', {
                    'unpaired_workers': online_workers
                })
        
        return view_func(request, *args, **kwargs)
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
    - Implements request-level caching to prevent multiple DB queries
    
    Args:
        request: Django request object
        
    Returns:
        SimpleUsers instance if valid, None otherwise
    """
    # Check cache first
    if hasattr(request, '_cached_user'):
        return request._cached_user

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
        # Update user's last authenticated request timestamp
        # This tracks actual authenticated requests to detect when cookies are cleared
        # More reliable than session data which can persist for days
        from django.utils import timezone
        user.last_authenticated_request = timezone.now()
        user.save(update_fields=['last_authenticated_request'])
        # Cache for subsequent calls in same request
        request._cached_user = user
        return user
    except SimpleUsers.DoesNotExist:
        # User was deleted - clear session to prevent orphaned sessions
        request.session.flush()
        return None
    except Exception:
        # Unexpected error - fail securely
        return None
