from django.db.models import F
from django.db.models.functions import Lower
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from SaveNLoad.services.redis_worker_service import get_user_workers
from SaveNLoad.utils.image_utils import get_image_url_or_fallback
from SaveNLoad.views.dashboard import _get_annotated_games, format_last_played
from SaveNLoad.views.custom_decorators import get_current_user
from SaveNLoad.views.input_sanitizer import sanitize_search_query
from SaveNLoad.views.api_helpers import get_game_save_locations


def _user_payload(user):
    return {
        'id': user.id,
        'username': user.username,
        'role': 'admin' if user.is_admin() else 'user',
        'email': user.email
    }


def _available_games_payload(user, queryset):
    games = []
    for game in queryset:
        last_played = game.user_last_played
        save_locations = get_game_save_locations(game)
        games.append({
            'id': game.id,
            'title': game.name,
            'image': get_image_url_or_fallback(game),
            'footer': format_last_played(last_played),
            'last_played_timestamp': last_played.isoformat() if last_played else None,
            'save_file_locations': save_locations
        })
    return games


class DashboardView(APIView):
    def get(self, request):
        user = get_current_user(request)
        if not user:
            return Response(
                {'error': 'Not authenticated. Please log in.', 'requires_login': True},
                status=status.HTTP_401_UNAUTHORIZED
            )

        worker_ids = get_user_workers(user.id)
        if not worker_ids:
            return Response(
                {
                    'error': 'Client worker not connected. Please ensure the client worker is running and claimed.',
                    'requires_worker': True
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        annotated_games = _get_annotated_games(user)
        recent_db_games = annotated_games.filter(
            user_last_played__isnull=False
        ).order_by('-user_last_played')[:10]

        recent_games = []
        for game in recent_db_games:
            recent_games.append({
                'id': game.id,
                'title': game.name,
                'image': get_image_url_or_fallback(game),
                'footer': format_last_played(game.user_last_played),
                'last_played_timestamp': game.user_last_played.isoformat() if game.user_last_played else None
            })

        available_db_games = annotated_games.order_by(Lower('name'), 'id')
        available_games = _available_games_payload(user, available_db_games)

        return Response(
            {
                'user': _user_payload(user),
                'is_admin': user.is_admin(),
                'recent_games': recent_games,
                'available_games': available_games
            },
            status=status.HTTP_200_OK
        )


class GameSearchView(APIView):
    def get(self, request):
        user = get_current_user(request)
        if not user:
            return Response(
                {'error': 'Not authenticated. Please log in.', 'requires_login': True},
                status=status.HTTP_401_UNAUTHORIZED
            )

        raw_search_query = request.GET.get('q', '').strip()
        search_query = sanitize_search_query(raw_search_query) if raw_search_query else None
        sort_by = request.GET.get('sort', 'name_asc')

        db_games = _get_annotated_games(user)

        if search_query:
            db_games = db_games.filter(name__icontains=search_query)

        if sort_by == 'name_desc':
            db_games = db_games.order_by(Lower('name').desc(), 'id')
        elif sort_by == 'last_saved_desc':
            db_games = db_games.filter(user_last_played__isnull=False).order_by(F('user_last_played').desc(), Lower('name'))
        elif sort_by == 'last_saved_asc':
            db_games = db_games.filter(user_last_played__isnull=False).order_by(F('user_last_played').asc(), Lower('name'))
        else:
            db_games = db_games.order_by(Lower('name'), 'id')

        games = _available_games_payload(user, db_games)

        return Response(
            {
                'games': games,
                'count': len(games)
            },
            status=status.HTTP_200_OK
        )
