from django.urls import include, path

urlpatterns = [
    path('', include('SaveNLoad.url_configs.api.dashboard')),
    path('', include('SaveNLoad.url_configs.api.meta')),
    path('', include('SaveNLoad.url_configs.api.auth')),
]
