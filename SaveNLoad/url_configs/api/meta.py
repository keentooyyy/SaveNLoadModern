from django.urls import path

from SaveNLoad.views import meta

urlpatterns = [
    path('meta/version', meta.version_view, name='version'),
]
