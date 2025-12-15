from django.urls import path
from ...views import dashboard, settings

app_name = 'admin'

urlpatterns = [
    path('dashboard/', dashboard.admin_dashboard, name='dashboard'),
    path('settings/', settings.settings_view, name='settings'),
    path('settings/search/', settings.search_game, name='search_game'),
]

