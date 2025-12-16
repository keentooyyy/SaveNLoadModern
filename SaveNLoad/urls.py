from django.urls import path
from SaveNLoad.views import auth

app_name = 'SaveNLoad'

urlpatterns = [
    path('', auth.login, name='login'),
    path('register/', auth.register, name='register'),
    path('forgot-password/', auth.forgot_password, name='forgot_password'),
    path('logout/', auth.logout, name='logout'),
    path('worker-required/', auth.worker_required, name='worker_required'),
]

