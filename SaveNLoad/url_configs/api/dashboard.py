from django.urls import path

from SaveNLoad.views import dashboard

urlpatterns = [
    path('dashboard', dashboard.dashboard_view, name='dashboard'),
    path('games/search', dashboard.game_search_view, name='game_search'),
]
