from django.urls import include, path

urlpatterns = [
    path('', include('SaveNLoad.url_configs.api.dashboard')),
    path('', include('SaveNLoad.url_configs.api.meta')),
    path('', include('SaveNLoad.url_configs.api.auth')),
    path('', include('SaveNLoad.url_configs.api.save_load')),
    path('', include('SaveNLoad.url_configs.api.settings')),
    path('client/', include('SaveNLoad.url_configs.client_worker.urls')),
]
