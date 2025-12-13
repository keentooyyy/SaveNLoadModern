from django.urls import path
from . import views

app_name = 'SaveNLoad'

urlpatterns = [
    path('', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
]

