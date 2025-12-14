from django.shortcuts import render, redirect
from django.urls import reverse
from .custom_decorators import login_required, get_current_user
from ..models import SimpleUsers


@login_required
def admin_dashboard(request):
    """Admin dashboard"""
    user = get_current_user(request)
    if not user or not user.is_admin():
        # Redirect non-admin users to their dashboard
        return redirect(reverse('user:dashboard'))
    
    return render(request, 'SaveNLoad/admin/dashboard.html')


@login_required
def user_dashboard(request):
    """User dashboard"""
    return render(request, 'SaveNLoad/user/dashboard.html')

