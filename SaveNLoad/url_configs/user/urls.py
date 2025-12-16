from django.urls import path
from SaveNLoad.views import dashboard, settings

app_name = 'user'

urlpatterns = [
    path('dashboard/', dashboard.user_dashboard, name='dashboard'),
    path('settings/', settings.user_settings_view, name='settings'),
]

