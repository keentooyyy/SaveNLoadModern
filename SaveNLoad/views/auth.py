from datetime import timedelta

import jwt
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django_ratelimit.decorators import ratelimit
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from SaveNLoad.models import SimpleUsers, UserRole
from SaveNLoad.models.password_reset_otp import PasswordResetOTP
from SaveNLoad.utils.email_service import send_otp_email
from SaveNLoad.utils.jwt_utils import (
    issue_access_token,
    issue_refresh_token,
    issue_reset_token,
    decode_token,
    find_active_refresh_token,
    revoke_refresh_token,
    revoke_all_refresh_tokens
)
from SaveNLoad.views.input_sanitizer import (
    sanitize_username,
    sanitize_email,
    validate_username_format,
    validate_password_strength
)


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


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CsrfView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'message': 'CSRF cookie set.'}, status=status.HTTP_200_OK)


@method_decorator(ratelimit(key='ip', rate='5/m', block=True), name='post')
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
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
            return _json_error('Invalid username/email or password.', field_errors, status.HTTP_401_UNAUTHORIZED)

        access_token = issue_access_token(user)
        refresh_days = settings.AUTH_REFRESH_TOKEN_DAYS if remember_me else settings.AUTH_REFRESH_TOKEN_SHORT_DAYS
        refresh_token = issue_refresh_token(
            user,
            refresh_days,
            user_agent=request.headers.get('User-Agent'),
            ip_address=_get_client_ip(request)
        )

        response = Response(
            {
                'message': 'Login successful.',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'role': user.role
                }
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


@method_decorator(ratelimit(key='ip', rate='3/m', block=True), name='post')
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = sanitize_username(request.data.get('username'))
        email = sanitize_email(request.data.get('email'))
        password = request.data.get('password') or ''
        repeat_password = request.data.get('repeatPassword') or ''

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

        if password != repeat_password:
            field_errors['repeatPassword'] = 'Passwords do not match.'

        if field_errors:
            return _json_error('Please fix the errors below.', field_errors)

        user = SimpleUsers(
            username=username,
            email=email,
            role=UserRole.USER
        )
        user.set_password(password)
        user.save()

        return Response({'message': 'Account created successfully. Please login.'}, status=status.HTTP_201_CREATED)


@method_decorator(ratelimit(key='ip', rate='5/m', block=True), name='post')
class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw_email = request.data.get('email', '').strip()
        email = sanitize_email(raw_email)

        if not email:
            return _json_error('Please enter a valid email address.')

        try:
            user = SimpleUsers.objects.get(email__iexact=email)
        except SimpleUsers.DoesNotExist:
            # Avoid account enumeration.
            return Response({'message': 'If the email exists, an OTP was sent.'}, status=status.HTTP_200_OK)

        try:
            otp = PasswordResetOTP.generate_otp(user, user.email, expiry_minutes=10)
            email_sent = send_otp_email(user.email, otp.otp_code, user.username)
            if not email_sent:
                return _json_error('Failed to send email. Please try again later.', http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception:
            return _json_error('An error occurred. Please try again later.', http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'message': 'If the email exists, an OTP was sent.'}, status=status.HTTP_200_OK)


@method_decorator(ratelimit(key='ip', rate='5/m', block=True), name='post')
class VerifyOtpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
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
                    return _json_error('Failed to send email. Please try again later.', http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except SimpleUsers.DoesNotExist:
                return Response({'message': 'If the email exists, an OTP was sent.'}, status=status.HTTP_200_OK)
            except Exception:
                return _json_error('An error occurred. Please try again later.', http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({'message': 'If the email exists, an OTP was sent.'}, status=status.HTTP_200_OK)

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


@method_decorator(ratelimit(key='ip', rate='5/m', block=True), name='post')
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
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


@method_decorator(ratelimit(key='ip', rate='30/m', block=True), name='post')
class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
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
        new_refresh_token = issue_refresh_token(
            user,
            settings.AUTH_REFRESH_TOKEN_DAYS,
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
            max_age=int(timedelta(days=settings.AUTH_REFRESH_TOKEN_DAYS).total_seconds())
        )
        return response


@method_decorator(ratelimit(key='ip', rate='30/m', block=True), name='post')
class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
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
