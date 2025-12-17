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
    json_response_field_errors,
    json_response_error,
    json_response_success,
    parse_json_body
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
                        # Session expires in 1 day (86400 seconds) - standard practice
                        request.session.set_expiry(86400)
                    else:
                        # Session expires in 2 weeks (1209600 seconds) when "Remember Me" is checked
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
    """Forgot password page - sends OTP via email"""
    # Check if already logged in
    redirect_response = redirect_if_logged_in(request)
    if redirect_response:
        return redirect_response
    
    if request.method == 'POST':
        # Handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from SaveNLoad.models.password_reset_otp import PasswordResetOTP
            from SaveNLoad.utils.email_service import send_otp_email
            import logging
            
            logger = logging.getLogger(__name__)
            
            data, error_response = parse_json_body(request)
            if error_response:
                return error_response
            
            # Sanitize email
            raw_email = data.get('email', '').strip()
            email = sanitize_email(raw_email)
            
            if not email:
                return json_response_error('Please enter a valid email address.', status=400)
            
            # Check if user exists with this email - ONLY send OTP to registered emails
            try:
                user = SimpleUsers.objects.get(email__iexact=email)
            except SimpleUsers.DoesNotExist:
                # User doesn't exist - return error message
                return json_response_error(
                    'Email not found. This email address is not registered. Please check your email or create an account.',
                    status=404
                )
            
            # User exists - verify we're using the registered email (not the input)
            # This ensures we only send to the exact email stored in the database
            registered_email = user.email
            
            # Generate OTP using the registered email
            try:
                otp = PasswordResetOTP.generate_otp(user, registered_email, expiry_minutes=10)
                
                # Send OTP via email - ONLY to the registered email address
                email_sent = send_otp_email(registered_email, otp.otp_code, user.username)
                
                if email_sent:
                    # Store registered email in session for OTP verification step
                    request.session['password_reset_email'] = registered_email
                    request.session['password_reset_user_id'] = user.id
                    # Clear any previous OTP verification
                    request.session.pop('password_reset_otp_verified', None)
                    
                    return json_response_success(
                        message='OTP code has been sent to your email address. Please check your inbox.'
                    )
                else:
                    logger.error(f"Failed to send OTP email to registered email: {registered_email}")
                    return json_response_error(
                        'Failed to send email. Please try again later.',
                        status=500
                    )
            except Exception as e:
                logger.error(f"Error generating/sending OTP: {str(e)}")
                return json_response_error(
                    'An error occurred. Please try again later.',
                    status=500
                )
    
    return render(request, 'SaveNLoad/forgot_password.html')


@ensure_csrf_cookie
@csrf_protect
def verify_otp(request):
    """Verify OTP page - validates OTP code"""
    # Check if already logged in
    redirect_response = redirect_if_logged_in(request)
    if redirect_response:
        return redirect_response
    
    # Check if email is in session (from forgot_password step)
    email = request.session.get('password_reset_email')
    if not email:
        # No email in session, redirect to forgot password
        return redirect(reverse('SaveNLoad:forgot_password'))
    
    if request.method == 'POST':
        # Handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from SaveNLoad.models.password_reset_otp import PasswordResetOTP
            from SaveNLoad.utils.email_service import send_otp_email
            import logging
            
            logger = logging.getLogger(__name__)
            
            data, error_response = parse_json_body(request)
            if error_response:
                return error_response
            
            action = data.get('action', 'verify')
            
            if action == 'resend':
                # Resend OTP - only to registered email
                try:
                    user = SimpleUsers.objects.get(email__iexact=email)
                    # Use the registered email from database, not the session email
                    registered_email = user.email
                    otp = PasswordResetOTP.generate_otp(user, registered_email, expiry_minutes=10)
                    email_sent = send_otp_email(registered_email, otp.otp_code, user.username)
                    
                    if email_sent:
                        return json_response_success(
                            message='A new OTP code has been sent to your email address.'
                        )
                    else:
                        logger.error(f"Failed to resend OTP email to {email}")
                        return json_response_error(
                            'Failed to send email. Please try again later.',
                            status=500
                        )
                except SimpleUsers.DoesNotExist:
                    return json_response_error('User not found.', status=404)
                except Exception as e:
                    logger.error(f"Error resending OTP: {str(e)}")
                    return json_response_error(
                        'An error occurred. Please try again later.',
                        status=500
                    )
            
            # Verify OTP
            otp_code = data.get('otp_code', '').strip()
            
            if not otp_code:
                return json_response_error('OTP code is required.', status=400)
            
            # Validate OTP - must match the email in session
            otp = PasswordResetOTP.validate_otp(email, otp_code)
            if not otp:
                return json_response_error('Invalid or expired OTP code.', status=400)
            
            # Verify OTP belongs to the correct user (prevent IDOR)
            user_id = request.session.get('password_reset_user_id')
            if otp.user.id != user_id:
                return json_response_error('Invalid OTP code.', status=400)
            
            # Mark OTP as verified in session
            request.session['password_reset_otp_verified'] = True
            request.session['password_reset_otp_id'] = otp.id
            
            # Redirect to reset password page
            redirect_url = reverse('SaveNLoad:reset_password')
            return json_response_with_redirect(
                message='OTP verified successfully!',
                redirect_url=redirect_url
            )
    
    # GET request - show verify OTP form
    return render(request, 'SaveNLoad/verify_otp.html', {
        'email': email
    })


@ensure_csrf_cookie
@csrf_protect
def reset_password(request):
    """Reset password page - sets new password after OTP verification"""
    # Check if already logged in
    redirect_response = redirect_if_logged_in(request)
    if redirect_response:
        return redirect_response
    
    # Check if email and OTP verification are in session
    email = request.session.get('password_reset_email')
    otp_verified = request.session.get('password_reset_otp_verified')
    otp_id = request.session.get('password_reset_otp_id')
    
    if not email or not otp_verified or not otp_id:
        # Missing required session data, redirect to forgot password
        return redirect(reverse('SaveNLoad:forgot_password'))
    
    if request.method == 'POST':
        # Handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from SaveNLoad.models.password_reset_otp import PasswordResetOTP
            import logging
            
            logger = logging.getLogger(__name__)
            
            data, error_response = parse_json_body(request)
            if error_response:
                return error_response
            
            new_password = data.get('new_password', '').strip()
            confirm_password = data.get('confirm_password', '').strip()
            
            # Validate inputs
            if not new_password:
                return json_response_error('New password is required.', status=400)
            
            if not confirm_password:
                return json_response_error('Please confirm your new password.', status=400)
            
            if new_password != confirm_password:
                return json_response_error('Passwords do not match.', status=400)
            
            # Validate password strength
            is_valid, error_msg = validate_password_strength(new_password)
            if not is_valid:
                return json_response_error(error_msg, status=400)
            
            # Verify OTP is still valid and matches session
            try:
                otp = PasswordResetOTP.objects.get(id=otp_id, email__iexact=email, is_used=False)
                
                if not otp.is_valid():
                    return json_response_error('OTP has expired. Please request a new one.', status=400)
                
                # Verify OTP belongs to the correct user (prevent IDOR)
                user_id = request.session.get('password_reset_user_id')
                if otp.user.id != user_id:
                    return json_response_error('Invalid session. Please start over.', status=400)
                
                # Reset password
                user = otp.user
                user.set_password(new_password)
                user.save()
                
                # Mark OTP as used
                otp.mark_as_used()
                
                # Clear session data
                request.session.pop('password_reset_email', None)
                request.session.pop('password_reset_user_id', None)
                request.session.pop('password_reset_otp_verified', None)
                request.session.pop('password_reset_otp_id', None)
                
                # Redirect to login
                redirect_url = reverse('SaveNLoad:login')
                return json_response_with_redirect(
                    message='Password reset successfully! Please login with your new password.',
                    redirect_url=redirect_url
                )
            except PasswordResetOTP.DoesNotExist:
                return json_response_error('Invalid session. Please start over.', status=400)
            except Exception as e:
                logger.error(f"Error resetting password: {str(e)}")
                return json_response_error(
                    'An error occurred. Please try again.',
                    status=500
                )
    
    # GET request - show reset password form
    return render(request, 'SaveNLoad/reset_password.html', {
        'email': email
    })


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
