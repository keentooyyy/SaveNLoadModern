"""
Shared helpers and DRF views for dashboard data.
"""
from datetime import timedelta

from django.db.models import Subquery, OuterRef, F
from django.db.models.functions import Lower
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from SaveNLoad.models import Game
from SaveNLoad.models.save_folder import SaveFolder
from SaveNLoad.services.redis_worker_service import get_user_workers
from SaveNLoad.utils.image_utils import get_image_url_or_fallback
from SaveNLoad.views.custom_decorators import get_current_user
from SaveNLoad.views.input_sanitizer import sanitize_search_query
from SaveNLoad.views.api_helpers import get_game_save_locations


def format_last_played(last_played):
    """
    Format last_played datetime as a human-readable string.
    """
    if not last_played:
        return "Never played"

    now = timezone.now()
    diff = now - last_played

    if diff < timedelta(minutes=1):
        return "Last played just now"
    if diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"Last played {minutes} min{'s' if minutes != 1 else ''} ago"
    if diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"Last played {hours} hour{'s' if hours != 1 else ''} ago"
    if diff < timedelta(days=7):
        days = diff.days
        return f"Last played {days} day{'s' if days != 1 else ''} ago"
    if diff < timedelta(days=30):
        weeks = int(diff.days / 7)
        return f"Last played {weeks} week{'s' if weeks != 1 else ''} ago"
    if diff < timedelta(days=365):
        months = int(diff.days / 30)
        return f"Last played {months} month{'s' if months != 1 else ''} ago"

    years = int(diff.days / 365)
    return f"Last played {years} year{'s' if years != 1 else ''} ago"


def _get_annotated_games(user):
    """
    Get games queryset annotated with user's specific last_played timestamp.
    """
    last_played_subquery = SaveFolder.objects.filter(
        game=OuterRef('pk'),
        user=user
    ).order_by('-created_at').values('created_at')[:1]

    return Game.objects.annotate(
        user_last_played=Subquery(last_played_subquery)
    )


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


def _dashboard_payload(user):
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

    return {
        'user': _user_payload(user),
        'is_admin': user.is_admin(),
        'recent_games': recent_games,
        'available_games': available_games
    }


@api_view(["GET"])
def dashboard_view(request):
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

    return Response(_dashboard_payload(user), status=status.HTTP_200_OK)


@api_view(["GET"])
def game_search_view(request):
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
        db_games = db_games.filter(user_last_played__isnull=False).order_by(
            F('user_last_played').desc(),
            Lower('name')
        )
    elif sort_by == 'last_saved_asc':
        db_games = db_games.filter(user_last_played__isnull=False).order_by(
            F('user_last_played').asc(),
            Lower('name')
        )
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
