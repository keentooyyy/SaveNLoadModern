from django.urls import path
from SaveNLoad.views import dashboard, settings, save_load_api

app_name = 'admin'

urlpatterns = [
    path('dashboard/', dashboard.admin_dashboard, name='dashboard'),
    path('games/search/', dashboard.search_available_games, name='search_available_games'),
    path('settings/', settings.settings_view, name='settings'),
    path('settings/search/', settings.search_game, name='search_game'),
    path('games/create/', settings.create_game, name='create_game'),
    # More specific patterns first to avoid conflicts
    path('games/<int:game_id>/save-folders/<int:folder_number>/delete/', save_load_api.delete_save_folder, name='delete_save_folder'),
    path('games/<int:game_id>/backup-all-saves/', save_load_api.backup_all_saves, name='backup_all_saves'),
    path('games/<int:game_id>/delete-all-saves/', save_load_api.delete_all_saves, name='delete_all_saves'),
    path('games/<int:game_id>/save-folders/', save_load_api.list_save_folders, name='list_save_folders'),
    path('games/<int:game_id>/saves/', save_load_api.list_saves, name='list_saves'),
    path('games/<int:game_id>/load/', save_load_api.load_game, name='load_game'),
    path('games/<int:game_id>/save/', save_load_api.save_game, name='save_game'),
    path('games/<int:game_id>/delete/', settings.delete_game, name='game_delete'),
    path('games/<int:game_id>/', settings.game_detail, name='game_detail'),
    path('operations/<int:operation_id>/status/', save_load_api.check_operation_status, name='check_operation_status'),
    path('account/update/', settings.update_account_settings, name='update_account_settings'),
    path('operations/queue/stats/', settings.operation_queue_stats, name='operation_queue_stats'),
    path('operations/queue/cleanup/', settings.operation_queue_cleanup, name='operation_queue_cleanup'),
]

