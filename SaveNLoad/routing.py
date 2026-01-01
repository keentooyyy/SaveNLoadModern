from django.urls import re_path
from SaveNLoad.ws_consumers.worker_consumer import WorkerConsumer
from SaveNLoad.ws_consumers.worker_list_consumer import WorkerListConsumer
from SaveNLoad.ws_consumers.worker_status_consumer import UserWorkerStatusConsumer

websocket_urlpatterns = [
    re_path(r'^ws/worker/(?P<client_id>[^/]+)/$', WorkerConsumer.as_asgi()),
    re_path(r'^ws/ui/workers/$', WorkerListConsumer.as_asgi()),
    re_path(r'^ws/ui/worker-status/$', UserWorkerStatusConsumer.as_asgi()),
]
