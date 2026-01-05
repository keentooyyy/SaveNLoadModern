from django.urls import path

from SaveNLoad.views import meta

urlpatterns = [
    path('meta/version', meta.VersionView.as_view(), name='version'),
]
