from django.urls import path
from SaveNLoad.views import client_worker_api

app_name = 'client_worker'

urlpatterns = [
    path('register/', client_worker_api.register_client, name='register'),
    path('ping/<str:client_id>/', client_worker_api.ping_worker, name='ping'),
    path('unregister/', client_worker_api.unregister_client, name='unregister'),
    path('check/', client_worker_api.check_connection, name='check'),
    path('pending/<str:client_id>/', client_worker_api.get_pending_operations, name='pending'),
    path('progress/<int:operation_id>/', client_worker_api.update_operation_progress, name='update_progress'),
    path('complete/<int:operation_id>/', client_worker_api.complete_operation, name='complete'),
    
    # Association endpoints
    path('unpaired/', client_worker_api.get_unpaired_workers, name='unpaired'),
    path('claim/', client_worker_api.claim_worker, name='claim'),
    path('unclaim/', client_worker_api.unclaim_worker, name='unclaim'),
]

