from django.urls import path
from ...views import dashboard

app_name = 'admin'

urlpatterns = [
    path('dashboard/', dashboard.admin_dashboard, name='dashboard'),
]

