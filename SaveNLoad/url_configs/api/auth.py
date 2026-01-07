from django.urls import path

from SaveNLoad.views import auth

urlpatterns = [
    path('auth/csrf', auth.csrf_view, name='csrf'),
    path('auth/login', auth.login_view, name='login'),
    path('auth/guest', auth.guest_view, name='guest'),
    path('auth/upgrade', auth.upgrade_view, name='upgrade'),
    path('auth/register', auth.register_view, name='register'),
    path('auth/forgot-password', auth.forgot_password_view, name='forgot_password'),
    path('auth/verify-otp', auth.verify_otp_view, name='verify_otp'),
    path('auth/reset-password', auth.reset_password_view, name='reset_password'),
    path('auth/refresh', auth.refresh_token_view, name='refresh'),
    path('auth/logout', auth.logout_view, name='logout'),
    path('auth/me', auth.me_view, name='me'),
    path('auth/ws-token/', auth.ws_token_view, name='ws_token'),
]
