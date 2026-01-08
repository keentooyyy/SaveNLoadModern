from datetime import timedelta
import secrets
import uuid

import jwt
from django.conf import settings
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django_ratelimit.decorators import ratelimit
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from rest_framework.authentication import BaseAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework import status

from SaveNLoad.models import SimpleUsers, UserRole
from SaveNLoad.models.password_reset_otp import PasswordResetOTP
from SaveNLoad.utils.email_service import send_otp_email
from SaveNLoad.utils.jwt_utils import (
    issue_access_token,
    issue_refresh_token,
    issue_refresh_token_with_exp,
    issue_reset_token,
    decode_token,
    find_active_refresh_token,
    revoke_refresh_token,
    revoke_all_refresh_tokens
)
from SaveNLoad.services.ws_ui_token_service import issue_ui_ws_token
from SaveNLoad.services.redis_worker_service import unclaim_user_workers
from SaveNLoad.views.input_sanitizer import (
    sanitize_username,
    sanitize_email,
    validate_username_format,
    validate_password_strength
)
from SaveNLoad.views.custom_decorators import get_current_user
from SaveNLoad.views.api_helpers import build_user_payload
from SaveNLoad.utils.system_settings import get_setting_value, is_feature_enabled


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


def _json_error(message, errors=None, http_status=status.HTTP_400_BAD_REQUEST):
    payload = {'message': message}
    if errors:
        payload['errors'] = errors
    return Response(payload, status=http_status)


def _set_cookie(response, name, value, max_age, path='/'):
    response.set_cookie(
        name,
        value,
        max_age=max_age,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path=path
    )


def _clear_cookie(response, name, path='/'):
    response.delete_cookie(name, path=path)


def _get_client_ip(request):
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _feature_disabled_response(message: str):
    return Response({'feature_disabled': True, 'message': message}, status=status.HTTP_403_FORBIDDEN)


def _build_login_response(user, remember_me=False, user_agent=None, ip_address=None):
    access_token = issue_access_token(user)
    refresh_days = settings.AUTH_REFRESH_TOKEN_DAYS if remember_me else settings.AUTH_REFRESH_TOKEN_SHORT_DAYS
    refresh_token = issue_refresh_token(
        user,
        refresh_days,
        user_agent=user_agent,
        ip_address=ip_address
    )

    response = Response(
        {
            'message': 'Login successful.',
            'user': build_user_payload(user)
        },
        status=status.HTTP_200_OK
    )

    _set_cookie(
        response,
        settings.AUTH_ACCESS_COOKIE_NAME,
        access_token,
        max_age=int(timedelta(minutes=settings.AUTH_ACCESS_TOKEN_MINUTES).total_seconds())
    )
    _set_cookie(
        response,
        settings.AUTH_REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=int(timedelta(days=refresh_days).total_seconds())
    )
    return response


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf_view(request):
    token = get_token(request)
    response = Response(
        {'message': 'CSRF cookie set.', 'csrfToken': token},
        status=status.HTTP_200_OK
    )
    response.set_cookie(
        settings.CSRF_COOKIE_NAME,
        token,
        max_age=getattr(settings, 'CSRF_COOKIE_AGE', None),
        secure=settings.CSRF_COOKIE_SECURE,
        httponly=settings.CSRF_COOKIE_HTTPONLY,
        samesite=settings.CSRF_COOKIE_SAMESITE,
        path=getattr(settings, 'CSRF_COOKIE_PATH', '/'),
        domain=getattr(settings, 'CSRF_COOKIE_DOMAIN', None)
    )
    return response


@api_view(["POST"])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='5/m', block=True)
@csrf_protect
def login_view(request):
    username_or_email = request.data.get('username', '').strip()
    password = request.data.get('password') or ''
    remember_me = bool(request.data.get('rememberMe'))

    field_errors = {}

    if not username_or_email:
        field_errors['username'] = 'Username or email is required.'
    if not password:
        field_errors['password'] = 'Password is required.'
    if field_errors:
        return _json_error('Please fill in all required fields.', field_errors)

    user = None
    try:
        sanitized_username = sanitize_username(username_or_email)
        if sanitized_username:
            user = SimpleUsers.objects.get(username=sanitized_username)
    except SimpleUsers.DoesNotExist:
        pass

    if not user:
        try:
            sanitized_email = sanitize_email(username_or_email)
            if sanitized_email:
                user = SimpleUsers.objects.get(email__iexact=sanitized_email)
        except SimpleUsers.DoesNotExist:
            pass

    if not user or not user.check_password(password):
        field_errors['username'] = 'Invalid username/email or password.'
        field_errors['password'] = 'Invalid username/email or password.'
        return _json_error('Invalid username/email or password.', field_errors, status.HTTP_404_NOT_FOUND)

    return _build_login_response(
        user,
        remember_me=remember_me,
        user_agent=request.headers.get('User-Agent'),
        ip_address=_get_client_ip(request)
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='3/m', block=True)
@csrf_protect
def register_view(request):
    username = sanitize_username(request.data.get('username'))
    raw_email = request.data.get('email')
    email = sanitize_email(raw_email)
    password = request.data.get('password') or ''
    repeat_password = request.data.get('repeatPassword') or ''

    field_errors = {}
    email_required = bool(get_setting_value('feature.email.registration_required', True))

    if not username:
        field_errors['username'] = 'Username is required.'
    elif not validate_username_format(username):
        field_errors['username'] = (
            'Username must be 3-150 characters and contain only letters, numbers, underscores, and hyphens.'
        )
    elif SimpleUsers.objects.filter(username=username).exists():
        field_errors['username'] = 'Username already exists.'

    if email_required:
        if not email:
            field_errors['email'] = 'Email is required.'
        elif SimpleUsers.objects.filter(email=email).exists():
            field_errors['email'] = 'Email already exists.'
    else:
        if raw_email and not email:
            field_errors['email'] = 'Email is invalid.'
        if email:
            if SimpleUsers.objects.filter(email=email).exists():
                field_errors['email'] = 'Email already exists.'

    if not password:
        field_errors['password'] = 'Password is required.'
    else:
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            field_errors['password'] = error_msg

    if password != repeat_password:
        field_errors['repeatPassword'] = 'Passwords do not match.'

    if field_errors:
        return _json_error('Please fix the errors below.', field_errors)

    final_email = email
    if not email_required and not final_email:
        final_email = f"{username}@local"

    user = SimpleUsers(
        username=username,
        email=final_email,
        role=UserRole.USER
    )
    user.set_password(password)
    user.save()

    return Response({'message': 'Account created successfully. Please login.'}, status=status.HTTP_201_CREATED)


def _generate_guest_username():
    while True:
        candidate = f"guest_{secrets.token_hex(4)}"
        if not SimpleUsers.objects.filter(username=candidate).exists():
            return candidate


@api_view(["POST"])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='10/m', block=True)
@csrf_protect
def guest_view(request):
    if not is_feature_enabled('feature.guest.enabled'):
        return _feature_disabled_response('Guest accounts are disabled.')

    ttl_days = int(get_setting_value('feature.guest.ttl_days', 14) or 14)
    ttl_days = max(1, min(ttl_days, 14))

    username = _generate_guest_username()
    email = f"guest+{uuid.uuid4()}@local"
    raw_password = secrets.token_urlsafe(16)

    user = SimpleUsers(
        username=username,
        email=email,
        role=UserRole.USER,
        is_guest=True,
        guest_expires_at=timezone.now() + timedelta(days=ttl_days),
        guest_namespace=username,
        guest_migration_status=None
    )
    user.set_password(raw_password)
    user.save()

    response = _build_login_response(
        user,
        remember_me=False,
        user_agent=request.headers.get('User-Agent'),
        ip_address=_get_client_ip(request)
    )
    response.data['guest_credentials'] = {
        'username': username,
        'email': email,
        'password': raw_password
    }
    return response


@api_view(["POST"])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='5/m', block=True)
@csrf_protect
def upgrade_view(request):
    user = get_current_user(request)
    if not user:
        return _json_error('Not authenticated.', http_status=status.HTTP_401_UNAUTHORIZED)

    if not getattr(user, 'is_guest', False):
        return _json_error('Only guest accounts can be upgraded.', http_status=status.HTTP_400_BAD_REQUEST)

    if user.guest_migration_status == 'migrating':
        return _json_error('Guest migration already in progress.', http_status=status.HTTP_409_CONFLICT)
    if user.guest_expires_at and user.guest_expires_at <= timezone.now():
        return _json_error('Guest account has expired.', http_status=status.HTTP_401_UNAUTHORIZED)

    username = sanitize_username(request.data.get('username'))
    email = sanitize_email(request.data.get('email'))
    password = request.data.get('password') or ''

    field_errors = {}
    if not username:
        field_errors['username'] = 'Username is required.'
    elif not validate_username_format(username):
        field_errors['username'] = (
            'Username must be 3-150 characters and contain only letters, numbers, underscores, and hyphens.'
        )
    elif SimpleUsers.objects.filter(username=username).exists():
        field_errors['username'] = 'Username already exists.'

    if not email:
        field_errors['email'] = 'Email is required.'
    elif SimpleUsers.objects.filter(email=email).exists():
        field_errors['email'] = 'Email already exists.'

    if not password:
        field_errors['password'] = 'Password is required.'
    else:
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            field_errors['password'] = error_msg

    if field_errors:
        return _json_error('Please fix the errors below.', field_errors)

    from SaveNLoad.views.api_helpers import get_client_worker_or_error
    client_worker, error_response = get_client_worker_or_error(user, request)
    if error_response:
        return error_response

    user.guest_pending_username = username
    user.guest_pending_email = email
    user.guest_pending_password = make_password(password)
    user.guest_migration_status = 'migrating'
    user.save(update_fields=[
        'guest_pending_username',
        'guest_pending_email',
        'guest_pending_password',
        'guest_migration_status'
    ])

    from SaveNLoad.models.operation_constants import OperationType
    from SaveNLoad.services.redis_operation_service import create_operation

    operation_id = create_operation(
        {
            'operation_type': OperationType.COPY_USER_STORAGE,
            'operation_group': 'guest_upgrade',
            'user_id': user.id,
            'local_save_path': '',
            'remote_ftp_path': '',
            'source_ftp_path': user.guest_namespace or user.username,
            'destination_ftp_path': username
        },
        client_worker
    )

    return Response(
        {
            'message': 'Guest migration started.',
            'operation_id': operation_id
        },
        status=status.HTTP_202_ACCEPTED
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='5/m', block=True)
@csrf_protect
def forgot_password_view(request):
    if not is_feature_enabled('feature.email.enabled'):
        return _feature_disabled_response('Email feature is disabled.')
    if not get_setting_value('feature.email.registration_required', True):
        return _feature_disabled_response('Email registration is disabled.')
    raw_email = request.data.get('email', '').strip()
    email = sanitize_email(raw_email)

    if not email:
        return _json_error('Please enter a valid email address.')

    try:
        user = SimpleUsers.objects.get(email__iexact=email)
    except SimpleUsers.DoesNotExist:
        return _json_error('No account found for that email address.', http_status=status.HTTP_404_NOT_FOUND)

    try:
        otp = PasswordResetOTP.generate_otp(user, user.email, expiry_minutes=10)
        email_sent = send_otp_email(user.email, otp.otp_code, user.username)
        if not email_sent:
            return _json_error(
                'Failed to send email. Please try again later.',
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    except Exception:
        return _json_error('An error occurred. Please try again later.', http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({'message': 'An OTP code was sent to your email.'}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='5/m', block=True)
@csrf_protect
def verify_otp_view(request):
    if not is_feature_enabled('feature.email.enabled'):
        return _feature_disabled_response('Email feature is disabled.')
    if not get_setting_value('feature.email.registration_required', True):
        return _feature_disabled_response('Email registration is disabled.')
    email = sanitize_email(request.data.get('email', '').strip())
    otp_code = (request.data.get('otp_code') or '').strip()
    action = request.data.get('action', 'verify')

    if not email:
        return _json_error('Email is required.')

    if action == 'resend':
        try:
            user = SimpleUsers.objects.get(email__iexact=email)
            otp = PasswordResetOTP.generate_otp(user, user.email, expiry_minutes=10)
            email_sent = send_otp_email(user.email, otp.otp_code, user.username)
            if not email_sent:
                return _json_error(
                    'Failed to send email. Please try again later.',
                    http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except SimpleUsers.DoesNotExist:
            return _json_error('No account found for that email address.', http_status=status.HTTP_404_NOT_FOUND)
        except Exception:
            return _json_error('An error occurred. Please try again later.', http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'message': 'OTP code sent.'}, status=status.HTTP_200_OK)

    if not otp_code:
        return _json_error('OTP code is required.')

    otp = PasswordResetOTP.validate_otp(email, otp_code)
    if not otp:
        return _json_error('Invalid or expired OTP code.', http_status=status.HTTP_400_BAD_REQUEST)

    reset_token = issue_reset_token(otp.user, otp.id)
    response = Response({'message': 'OTP verified successfully.'}, status=status.HTTP_200_OK)
    _set_cookie(
        response,
        settings.AUTH_RESET_COOKIE_NAME,
        reset_token,
        max_age=int(timedelta(minutes=settings.AUTH_RESET_TOKEN_MINUTES).total_seconds())
    )
    return response


@api_view(["POST"])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='5/m', block=True)
@csrf_protect
def reset_password_view(request):
    if not is_feature_enabled('feature.email.enabled'):
        return _feature_disabled_response('Email feature is disabled.')
    if not get_setting_value('feature.email.registration_required', True):
        return _feature_disabled_response('Email registration is disabled.')
    reset_token = request.COOKIES.get(settings.AUTH_RESET_COOKIE_NAME)
    if not reset_token:
        return _json_error('Reset token missing or expired.', http_status=status.HTTP_401_UNAUTHORIZED)

    new_password = (request.data.get('new_password') or '').strip()
    confirm_password = (request.data.get('confirm_password') or '').strip()

    if not new_password:
        return _json_error('New password is required.')
    if not confirm_password:
        return _json_error('Please confirm your new password.')
    if new_password != confirm_password:
        return _json_error('Passwords do not match.')

    is_valid, error_msg = validate_password_strength(new_password)
    if not is_valid:
        return _json_error(error_msg)

    try:
        payload = decode_token(reset_token, 'reset')
        user_id = int(payload.get('sub', 0))
        otp_id = payload.get('otp_id')
    except (jwt.InvalidTokenError, ValueError):
        return _json_error('Invalid or expired reset token.', http_status=status.HTTP_401_UNAUTHORIZED)

    try:
        otp = PasswordResetOTP.objects.get(id=otp_id, user_id=user_id, is_used=False)
        if not otp.is_valid():
            return _json_error('OTP has expired. Please request a new one.')
    except PasswordResetOTP.DoesNotExist:
        return _json_error('Invalid reset token.')

    user = otp.user
    user.set_password(new_password)
    user.save()
    otp.mark_as_used()

    response = Response({'message': 'Password reset successfully.'}, status=status.HTTP_200_OK)
    _clear_cookie(response, settings.AUTH_RESET_COOKIE_NAME)
    return response


@api_view(["POST"])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='30/m', block=True)
@csrf_protect
def refresh_token_view(request):
    refresh_token = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
    if not refresh_token:
        return _json_error('Refresh token missing.', http_status=status.HTTP_401_UNAUTHORIZED)

    try:
        payload = decode_token(refresh_token, 'refresh')
        user_id = int(payload.get('sub', 0))
        jti = payload.get('jti')
    except (jwt.InvalidTokenError, ValueError):
        return _json_error('Invalid refresh token.', http_status=status.HTTP_401_UNAUTHORIZED)

    token_record = find_active_refresh_token(jti)
    if not token_record:
        revoke_all_refresh_tokens(user_id)
        return _json_error('Refresh token revoked.', http_status=status.HTTP_401_UNAUTHORIZED)

    try:
        user = SimpleUsers.objects.get(id=user_id)
    except SimpleUsers.DoesNotExist:
        return _json_error('User not found.', http_status=status.HTTP_401_UNAUTHORIZED)

    if not token_record.matches_context(
        request.headers.get('User-Agent'),
        _get_client_ip(request)
    ):
        revoke_all_refresh_tokens(user_id)
        return _json_error('Refresh token context mismatch.', http_status=status.HTTP_401_UNAUTHORIZED)

    access_token = issue_access_token(user)
    remaining_seconds = int((token_record.expires_at - timezone.now()).total_seconds())
    if remaining_seconds <= 0:
        revoke_refresh_token(jti)
        return _json_error('Refresh token expired.', http_status=status.HTTP_401_UNAUTHORIZED)
    new_refresh_token = issue_refresh_token_with_exp(
        user,
        token_record.expires_at,
        user_agent=request.headers.get('User-Agent'),
        ip_address=_get_client_ip(request)
    )
    new_payload = decode_token(new_refresh_token, 'refresh')
    revoke_refresh_token(jti, replaced_by=new_payload.get('jti'))

    response = Response({'message': 'Token refreshed.'}, status=status.HTTP_200_OK)
    _set_cookie(
        response,
        settings.AUTH_ACCESS_COOKIE_NAME,
        access_token,
        max_age=int(timedelta(minutes=settings.AUTH_ACCESS_TOKEN_MINUTES).total_seconds())
    )
    _set_cookie(
        response,
        settings.AUTH_REFRESH_COOKIE_NAME,
        new_refresh_token,
        max_age=remaining_seconds
    )
    return response


@api_view(["POST"])
@permission_classes([AllowAny])
@ratelimit(key='ip', rate='30/m', block=True)
@csrf_protect
def logout_view(request):
    user = get_current_user(request)
    if user:
        try:
            unclaim_user_workers(user.id)
        except Exception as exc:
            print(f"ERROR: Failed to unclaim workers on logout for user_id={user.id}: {exc}")

    refresh_token = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
    if refresh_token:
        try:
            payload = decode_token(refresh_token, 'refresh')
            revoke_refresh_token(payload.get('jti'))
        except jwt.InvalidTokenError:
            pass

    response = Response({'message': 'Logged out.'}, status=status.HTTP_200_OK)
    _clear_cookie(response, settings.AUTH_ACCESS_COOKIE_NAME)
    _clear_cookie(response, settings.AUTH_REFRESH_COOKIE_NAME)
    _clear_cookie(response, settings.AUTH_RESET_COOKIE_NAME)
    return response


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_protect
def ws_token_view(request):
    user = get_current_user(request)
    if not user:
        return _json_error('Not authenticated.', http_status=status.HTTP_401_UNAUTHORIZED)

    token = issue_ui_ws_token(user.id)
    return Response({'token': token}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
def me_view(request):
    user = get_current_user(request)
    if not user:
        return _json_error('Not authenticated.', http_status=status.HTTP_401_UNAUTHORIZED)

    return Response(
        {
            'user': build_user_payload(user)
        },
        status=status.HTTP_200_OK
    )
