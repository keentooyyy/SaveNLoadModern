from django.urls import path
from . import views

app_name = 'SaveNLoad'

urlpatterns = [
    path('', views.route_login, name='route_login'),
    path('register/', views.route_register, name='route_register'),
]

