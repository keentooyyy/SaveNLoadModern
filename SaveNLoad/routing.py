from django.urls import re_path
from SaveNLoad import consumers

websocket_urlpatterns = [
    re_path(r'^ws/worker/(?P<client_id>[^/]+)/$', consumers.WorkerConsumer.as_asgi()),
]
