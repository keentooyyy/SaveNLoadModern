from django.urls import path

from SaveNLoad.views import settings as settings_view

urlpatterns = [
    path('admin/settings', settings_view.admin_settings, name='admin_settings'),
    path('admin/settings/reveal', settings_view.admin_settings_reveal, name='admin_settings_reveal'),
    path('admin/settings/health', settings_view.admin_settings_health, name='admin_settings_health'),
    path('settings/public', settings_view.public_settings, name='public_settings'),
    path('settings/search', settings_view.search_game, name='search_game'),
    path('games/create/', settings_view.create_game, name='create_game'),
    path('account/update/', settings_view.update_account_settings, name='update_account_settings'),
    path('operations/queue/stats/', settings_view.operation_queue_stats, name='operation_queue_stats'),
    path('operations/queue/cleanup/', settings_view.operation_queue_cleanup, name='operation_queue_cleanup'),
    path('users/', settings_view.list_users, name='list_users'),
    path('users/<int:user_id>/reset-password/', settings_view.reset_user_password, name='reset_user_password'),
    path('users/<int:user_id>/delete/', settings_view.delete_user, name='delete_user'),
]
