from django.urls import path
from SaveNLoad.views import dashboard, settings, save_load_api

app_name = 'user'

urlpatterns = [
    path('dashboard/', dashboard.user_dashboard, name='dashboard'),
    path('games/search/', dashboard.search_available_games, name='search_available_games'),
    path('settings/', settings.user_settings_view, name='settings'),
    path('account/update/', settings.update_account_settings, name='update_account_settings'),
    path('games/<int:game_id>/backup-all-saves/', save_load_api.backup_all_saves, name='backup_all_saves'),
    path('games/<int:game_id>/delete-all-saves/', save_load_api.delete_all_saves, name='delete_all_saves'),
    path('games/<int:game_id>/save-location/', save_load_api.get_game_save_location, name='get_game_save_location'),
    path('games/<int:game_id>/open-save-location/', save_load_api.open_save_location, name='open_save_location'),
]

