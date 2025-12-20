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
    - Validates session exists
    - Validates user_id is a valid integer (prevents type confusion attacks)
    - Verifies user still exists in database (prevents deleted user access)
    - Clears invalid sessions automatically
    - Returns JSON error for AJAX requests instead of redirecting
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
        
        # Check if session exists
        if not hasattr(request, 'session'):
            if is_ajax:
                return JsonResponse({'error': 'Session not found. Please log in.', 'requires_login': True}, status=401)
            return redirect(reverse('SaveNLoad:login'))
        
        # Get user_id from session
        user_id = request.session.get('user_id')
        if not user_id:
            if is_ajax:
                return JsonResponse({'error': 'Not authenticated. Please log in.', 'requires_login': True}, status=401)
            return redirect(reverse('SaveNLoad:login'))
        
        # Validate user_id is a valid integer (prevent type confusion attacks)
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            # Invalid user_id type - clear session and redirect
            request.session.flush()
            if is_ajax:
                return JsonResponse({'error': 'Invalid session. Please log in again.', 'requires_login': True}, status=401)
            return redirect(reverse('SaveNLoad:login'))
        
        # Validate user_id is positive (prevent negative IDs or zero)
        if user_id <= 0:
            request.session.flush()
            if is_ajax:
                return JsonResponse({'error': 'Invalid session. Please log in again.', 'requires_login': True}, status=401)
            return redirect(reverse('SaveNLoad:login'))
        
        # Get user from database - verify it still exists
        try:
            user = SimpleUsers.objects.get(id=user_id)
            request.user = user  # Attach user to request
            return view_func(request, *args, **kwargs)
        except SimpleUsers.DoesNotExist:
            # User was deleted - clear session to prevent orphaned sessions
            request.session.flush()
            if is_ajax:
                return JsonResponse({'error': 'User not found. Please log in again.', 'requires_login': True}, status=401)
            return redirect(reverse('SaveNLoad:login'))
        except Exception:
            # Unexpected error - redirect to login
            request.session.flush()
            if is_ajax:
                return JsonResponse({'error': 'Authentication error. Please log in again.', 'requires_login': True}, status=401)
            return redirect(reverse('SaveNLoad:login'))
    return wrapper


def client_worker_required(view_func):
    """Decorator to ensure client worker is connected before allowing access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if any worker is connected
        if not ClientWorker.is_worker_connected():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # AJAX request - return JSON error
                return JsonResponse({
                    'error': 'Client worker not connected',
                    'requires_worker': True
                }, status=503)
            else:
                # Regular request - render worker required page directly
                return render(request, 'SaveNLoad/worker_required.html')
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
