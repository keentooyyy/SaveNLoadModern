from django.urls import path

from SaveNLoad.views import save_load_api

urlpatterns = [
    path('games/<int:game_id>/save/', save_load_api.save_game, name='save_game'),
    path('games/<int:game_id>/load/', save_load_api.load_game, name='load_game'),
    path('operations/<str:operation_id>/status/', save_load_api.check_operation_status, name='check_operation_status'),
]
