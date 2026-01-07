from django.urls import path

from SaveNLoad.views import client_worker_api

app_name = 'client_worker'

urlpatterns = [
    path('register/', client_worker_api.register_client, name='register'),
    path('unregister/', client_worker_api.unregister_client, name='unregister'),
    
    # Association endpoints
    path('unpaired/', client_worker_api.get_unpaired_workers, name='unpaired'),
    path('claim/', client_worker_api.claim_worker, name='claim'),
    path('unclaim/', client_worker_api.unclaim_worker, name='unclaim'),
    path('workers/', client_worker_api.list_workers, name='workers'),
    path('unclaim-all/', client_worker_api.unclaim_all_workers, name='unclaim_all'),
]

