from django.shortcuts import redirect
from django.urls import reverse
from functools import wraps
from SaveNLoad.models import SimpleUsers


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


def get_current_user(request):
    """Get current user from session"""
    user_id = request.session.get('user_id')
    if user_id:
        try:
            return SimpleUsers.objects.get(id=user_id)
        except SimpleUsers.DoesNotExist:
            return None
    return None

