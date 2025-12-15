from django.urls import path
from SaveNLoad.views import dashboard

app_name = 'user'

urlpatterns = [
    path('dashboard/', dashboard.user_dashboard, name='dashboard'),
]

