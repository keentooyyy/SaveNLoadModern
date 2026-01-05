from django.urls import path

from SaveNLoad.views import dashboard_api

urlpatterns = [
    path('dashboard', dashboard_api.DashboardView.as_view(), name='dashboard'),
    path('games/search', dashboard_api.GameSearchView.as_view(), name='game_search'),
]
