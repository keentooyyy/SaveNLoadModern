from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse
from functools import wraps
from SaveNLoad.models import SimpleUsers
from SaveNLoad.models.client_worker import ClientWorker


def login_required(view_func):
    """Custom login required decorator using sessions"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        if not user_id:
            return redirect(reverse('SaveNLoad:login'))
        try:
            user = SimpleUsers.objects.get(id=user_id)
            request.user = user  # Attach user to request
            return view_func(request, *args, **kwargs)
        except SimpleUsers.DoesNotExist:
            request.session.flush()
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
                # Regular request - redirect to worker required page
                return redirect(reverse('SaveNLoad:worker_required'))
        return view_func(request, *args, **kwargs)
    return wrapper


def get_current_user(request):
    """Get current user from session"""
    user_id = request.session.get('user_id')
    if user_id:
        try:
            return SimpleUsers.objects.get(id=user_id)
        except SimpleUsers.DoesNotExist:
            return None
    return None
