from django.urls import path

from SaveNLoad.views import save_load_api

urlpatterns = [
    path('games/<int:game_id>/save/', save_load_api.save_game, name='save_game'),
    path('games/<int:game_id>/load/', save_load_api.load_game, name='load_game'),
    path('games/<int:game_id>/save-folders/', save_load_api.list_save_folders, name='list_save_folders'),
    path('games/<int:game_id>/save-folders/<int:folder_number>/delete/', save_load_api.delete_save_folder, name='delete_save_folder'),
    path('games/<int:game_id>/backup-all-saves/', save_load_api.backup_all_saves, name='backup_all_saves'),
    path('games/<int:game_id>/delete-all-saves/', save_load_api.delete_all_saves, name='delete_all_saves'),
    path('games/<int:game_id>/open-save-location/', save_load_api.open_save_location, name='open_save_location'),
    path('games/<int:game_id>/save-location/', save_load_api.get_game_save_location, name='get_game_save_location'),
    path('operations/<str:operation_id>/status/', save_load_api.check_operation_status, name='check_operation_status'),
]
