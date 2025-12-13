from django.urls import path
from . import views

app_name = 'SaveNLoad'

urlpatterns = [
    path('', views.route_login, name='route_login'),
]

