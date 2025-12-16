from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.utils.html import escape

from SaveNLoad.models import SimpleUsers, UserRole
from SaveNLoad.views.custom_decorators import login_required, get_current_user
from SaveNLoad.views.api_helpers import (
    check_worker_connected_or_redirect,
    redirect_if_logged_in,
    json_response_with_redirect,
    json_response_field_errors
)
from SaveNLoad.views.input_sanitizer import (
    sanitize_username,
    sanitize_email,
    validate_username_format,
    validate_password_strength
)


@ensure_csrf_cookie
@csrf_protect
def login(request):
    """Login page and authentication - CSRF protected"""
    # Check if client worker is connected
    redirect_response = check_worker_connected_or_redirect()
    if redirect_response:
        return redirect_response
    
    # Check if already logged in
    redirect_response = redirect_if_logged_in(request)
    if redirect_response:
        return redirect_response
    
    if request.method == 'POST':
        # Sanitize and validate inputs
        username = sanitize_username(request.POST.get('username'))
        password = request.POST.get('password')
        remember_me = request.POST.get('rememberMe') == 'on'
        
        # Validation with field-specific errors
        field_errors = {}
        
        if not username:
            field_errors['username'] = 'Username is required.'
        
        if not password:
            field_errors['password'] = 'Password is required.'
        
        # Only handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if field_errors:
                return json_response_field_errors(
                    field_errors,
                    message='Please fill in all required fields.'
                )
            
            # Custom authentication - check user exists and password matches
            # Using Django ORM .get() prevents SQL injection
            try:
                user = SimpleUsers.objects.get(username=username)
                if user.check_password(password):
                    # Store user ID in session
                    request.session['user_id'] = user.id
                    
                    # Handle "Remember Me" functionality
                    if not remember_me:
                        # Session expires when browser closes
                        request.session.set_expiry(0)
                    else:
                        # Session expires in 2 weeks
                        request.session.set_expiry(1209600)
                    
                    # Server-side redirect for AJAX (via custom header)
                    if user.is_admin():
                        redirect_url = reverse('admin:dashboard')
                    else:
                        redirect_url = reverse('user:dashboard')
                    
                    # Escape username to prevent XSS in response
                    safe_username = escape(user.username)
                    return json_response_with_redirect(
                        message=f'Welcome back, {safe_username}!',
                        redirect_url=redirect_url
                    )
                else:
                    field_errors['username'] = 'Invalid username or password.'
                    field_errors['password'] = 'Invalid username or password.'
                    return json_response_field_errors(
                        field_errors,
                        message='Invalid username or password.'
                    )
            except SimpleUsers.DoesNotExist:
                field_errors['username'] = 'Invalid username or password.'
                field_errors['password'] = 'Invalid username or password.'
                return json_response_field_errors(
                    field_errors,
                    message='Invalid username or password.'
                )
    
    return render(request, 'SaveNLoad/login.html')


@ensure_csrf_cookie
@csrf_protect
def register(request):
    """Registration page and user creation - CSRF protected"""
    # Check if client worker is connected
    redirect_response = check_worker_connected_or_redirect()
    if redirect_response:
        return redirect_response
    
    # Check if already logged in
    redirect_response = redirect_if_logged_in(request)
    if redirect_response:
        return redirect_response
    
    if request.method == 'POST':
        # Sanitize and validate inputs
        username = sanitize_username(request.POST.get('username'))
        email = sanitize_email(request.POST.get('email'))
        password = request.POST.get('password')  # Password is hashed, no sanitization needed
        repeat_password = request.POST.get('repeatPassword')
        
        # Validation with field-specific errors
        field_errors = {}
        general_errors = []
        
        if not username:
            field_errors['username'] = 'Username is required.'
        elif not validate_username_format(username):
            field_errors['username'] = 'Username must be 3-150 characters and contain only letters, numbers, underscores, and hyphens.'
        # Using Django ORM .filter() prevents SQL injection
        elif SimpleUsers.objects.filter(username=username).exists():
            field_errors['username'] = 'Username already exists.'
        
        if not email:
            field_errors['email'] = 'Email is required.'
        # Using Django ORM .filter() prevents SQL injection
        elif SimpleUsers.objects.filter(email=email).exists():
            field_errors['email'] = 'Email already exists.'
        
        if not password:
            field_errors['password'] = 'Password is required.'
        else:
            is_valid, error_msg = validate_password_strength(password)
            if not is_valid:
                field_errors['password'] = error_msg
        
        if password != repeat_password:
            field_errors['repeatPassword'] = 'Passwords do not match.'
        
        # Only handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if field_errors or general_errors:
                return json_response_field_errors(field_errors, general_errors)
            else:
                # Create user
                try:
                    user = SimpleUsers(
                        username=username,
                        email=email,
                        role=UserRole.USER
                    )
                    user.set_password(password)
                    user.save()
                    
                    # Server-side redirect for AJAX (via custom header)
                    redirect_url = reverse('SaveNLoad:login')
                    return json_response_with_redirect(
                        message='Account created successfully! Please login.',
                        redirect_url=redirect_url
                    )
                except Exception as e:
                    # Don't expose internal error details to prevent information leakage
                    return json_response_error(
                        'An error occurred while creating your account. Please try again.',
                        status=400
                    )
    
    return render(request, 'SaveNLoad/register.html')


@ensure_csrf_cookie
@csrf_protect
def forgot_password(request):
    """Forgot password page - CSRF protected"""
    # Check if already logged in
    redirect_response = redirect_if_logged_in(request)
    if redirect_response:
        return redirect_response
    
    return render(request, 'SaveNLoad/forgot_password.html')


@login_required
def logout(request):
    """Logout and clear session"""
    request.session.flush()
    return redirect(reverse('SaveNLoad:login'))


def worker_required(request):
    """Page shown when client worker is not connected"""
    from SaveNLoad.models.client_worker import ClientWorker
    is_connected = ClientWorker.is_worker_connected()
    
    if is_connected:
        # Worker is connected, redirect to appropriate page
        redirect_response = redirect_if_logged_in(request)
        if redirect_response:
            return redirect_response
        else:
            # User is not logged in, redirect to login
            return redirect(reverse('SaveNLoad:login'))
    
    # No worker connected - show the worker required page
    # Get all active workers for display
    all_workers = ClientWorker.get_active_workers()
    
    return render(request, 'SaveNLoad/worker_required.html', {
        'all_workers': all_workers,
        'total_workers': len(all_workers)
    })
