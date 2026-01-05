from django.urls import path

from SaveNLoad.views import auth
from SaveNLoad.views import meta

app_name = 'SaveNLoad'

urlpatterns = [
    path('meta/version', meta.VersionView.as_view(), name='version'),
    path('auth/csrf', auth.CsrfView.as_view(), name='csrf'),
    path('auth/login', auth.LoginView.as_view(), name='login'),
    path('auth/register', auth.RegisterView.as_view(), name='register'),
    path('auth/forgot-password', auth.ForgotPasswordView.as_view(), name='forgot_password'),
    path('auth/verify-otp', auth.VerifyOtpView.as_view(), name='verify_otp'),
    path('auth/reset-password', auth.ResetPasswordView.as_view(), name='reset_password'),
    path('auth/refresh', auth.RefreshTokenView.as_view(), name='refresh'),
    path('auth/logout', auth.LogoutView.as_view(), name='logout'),
]

