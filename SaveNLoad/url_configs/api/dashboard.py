from django.urls import path

from SaveNLoad.views import dashboard

urlpatterns = [
    path('dashboard', dashboard.dashboard_view, name='dashboard'),
    path('dashboard/bootstrap', dashboard.dashboard_bootstrap_view, name='dashboard_bootstrap'),
    path('games/search', dashboard.game_search_view, name='game_search'),
]
