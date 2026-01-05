from django.urls import include, path

app_name = 'SaveNLoad'

urlpatterns = [
    path('', include('SaveNLoad.url_configs.api.urls')),
]

