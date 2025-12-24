"""
URL configuration for client worker API endpoints
"""
from django.urls import path
from SaveNLoad.views import client_worker_api

app_name = 'client_worker'

urlpatterns = [
    path('register/', client_worker_api.register_client, name='register'),
    path('heartbeat/', client_worker_api.heartbeat, name='heartbeat'),
    path('unregister/', client_worker_api.unregister_client, name='unregister'),
    path('check/', client_worker_api.check_connection, name='check'),
    path('operations/<str:client_id>/', client_worker_api.get_pending_operations, name='get_pending_operations'),
    path('progress/<int:operation_id>/', client_worker_api.update_operation_progress, name='update_operation_progress'),
    path('complete/<int:operation_id>/', client_worker_api.complete_operation, name='complete_operation'),
]

