from django.urls import path

from SaveNLoad.views import pages

urlpatterns = [
    path('', pages.home_page, name='home'),
    path('login', pages.login_page, name='page_login'),
    path('settings', pages.settings_page, name='settings'),
    path('dashboard', pages.dashboard_page, name='dashboard'),
    path('games/<int:game_id>', pages.game_detail_page, name='game_detail'),
    path('register', pages.register_page, name='register'),
    path('forgot-password', pages.forgot_password_page, name='forgot_password'),
    path('verify-otp', pages.verify_otp_page, name='verify_otp'),
    path('reset-password', pages.reset_password_page, name='reset_password'),
    path('worker-required', pages.worker_required_page, name='worker_required'),
]
