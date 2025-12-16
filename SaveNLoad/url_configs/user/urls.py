from django.urls import path
from SaveNLoad.views import dashboard, settings

app_name = 'user'

urlpatterns = [
    path('dashboard/', dashboard.user_dashboard, name='dashboard'),
    path('games/search/', dashboard.search_available_games, name='search_available_games'),
    path('settings/', settings.user_settings_view, name='settings'),
    path('account/change-password/', settings.change_password, name='change_password'),
]

