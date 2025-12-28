from django.urls import path
from SaveNLoad.views import auth

app_name = 'SaveNLoad'

urlpatterns = [
    path('', auth.login, name='login'),
    path('register/', auth.register, name='register'),
    path('forgot-password/', auth.forgot_password, name='forgot_password'),
    path('verify-otp/', auth.verify_otp, name='verify_otp'),
    path('reset-password/', auth.reset_password, name='reset_password'),
    path('logout/', auth.logout, name='logout'),

]

