from django.urls import path
from SaveNLoad.views import dashboard, settings

app_name = 'admin'

urlpatterns = [
    path('dashboard/', dashboard.admin_dashboard, name='dashboard'),
    path('settings/', settings.settings_view, name='settings'),
    path('settings/search/', settings.search_game, name='search_game'),
    path('games/<int:game_id>/', settings.game_detail, name='game_detail'),
    path('games/<int:game_id>/delete/', settings.delete_game, name='game_delete'),
]

