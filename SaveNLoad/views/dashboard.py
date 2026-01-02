import json
from datetime import timedelta

from django.db.models import Subquery, OuterRef, F
from django.db.models.functions import Lower
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from SaveNLoad.models import Game
from SaveNLoad.models.save_folder import SaveFolder
from SaveNLoad.services.redis_worker_service import get_user_workers, get_workers_snapshot
from SaveNLoad.utils.image_utils import get_image_url_or_fallback
from SaveNLoad.views.api_helpers import check_admin_or_error, get_game_save_locations
from SaveNLoad.views.custom_decorators import login_required, get_current_user, client_worker_required


def format_last_played(last_played):
    """
    Format last_played datetime as a human-readable string.

    Args:
        last_played: Datetime of last play or None.

    Returns:
        Human-readable string.
    """
    if not last_played:
        return "Never played"

    now = timezone.now()
    diff = now - last_played

    if diff < timedelta(minutes=1):
        return "Last played just now"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"Last played {minutes} min{'s' if minutes != 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"Last played {hours} hour{'s' if hours != 1 else ''} ago"
    elif diff < timedelta(days=7):
        days = diff.days
        return f"Last played {days} day{'s' if days != 1 else ''} ago"
    elif diff < timedelta(days=30):
        weeks = int(diff.days / 7)
        return f"Last played {weeks} week{'s' if weeks != 1 else ''} ago"
    elif diff < timedelta(days=365):
        months = int(diff.days / 30)
        return f"Last played {months} month{'s' if months != 1 else ''} ago"
    else:
        years = int(diff.days / 365)
        return f"Last played {years} year{'s' if years != 1 else ''} ago"


def _get_annotated_games(user):
    """
    Get games queryset annotated with user's specific last_played timestamp

    Args:
        user: User instance.

    Returns:
        QuerySet of annotated Game objects.
    """
    # Subquery to get the latest save creation time for each game for THIS user
    last_played_subquery = SaveFolder.objects.filter(
        game=OuterRef('pk'),
        user=user
    ).order_by('-created_at').values('created_at')[:1]

    return Game.objects.annotate(
        user_last_played=Subquery(last_played_subquery)
    )


def _get_dashboard_context_data(user):
    """
    Helper to get shared dashboard context data
    Returns: (recent_games, available_games)

    Args:
        user: User instance.

    Returns:
        Tuple of (recent_games, available_games).
    """
    # Optimized: Get annotated games directly
    # This replaces fetching ALL games and sorting in Python
    annotated_games = _get_annotated_games(user)

    # Recent games: Filter by having played, sort by date desc, limit 10
    # Use the annotated user_last_played field
    recent_db_games = annotated_games.filter(
        user_last_played__isnull=False
    ).order_by('-user_last_played')[:10]

    recent_games = []
    for game in recent_db_games:
        recent_games.append({
            'title': game.name,
            'image': get_image_url_or_fallback(game),
            'playtime': format_last_played(game.user_last_played),
        })

    # Available games section (all games)
    # Sort alphabetically by default for the main list
    # Use order_by(Lower('name'), 'id') for stable, case-insensitive sorting
    db_games = annotated_games.order_by(Lower('name'), 'id')
    available_games = []

    for game in db_games:
        # Use annotated field instead of map lookup
        last_played = game.user_last_played
        save_locations = get_game_save_locations(game)
        available_games.append({
            'id': game.id,
            'title': game.name,
            'image': get_image_url_or_fallback(game),
            'footer': format_last_played(last_played),
            'save_file_locations': save_locations,
            'save_file_locations_json': json.dumps(save_locations),
        })

    return recent_games, available_games


@login_required
@client_worker_required
def admin_dashboard(request):
    """
    Admin dashboard view.

    Args:
        request: Django request object.

    Returns:
        HttpResponse.
    """
    user = get_current_user(request)
    error_response = check_admin_or_error(user)
    if error_response:
        # Redirect non-admin users to their dashboard
        return redirect(reverse('user:dashboard'))

    recent_games, available_games = _get_dashboard_context_data(user)

    context = {
        'recent_games': recent_games,
        'available_games': available_games,
        'is_user': False,
        'user': user
    }

    return render(request, 'SaveNLoad/dashboard.html', context)


@login_required
@client_worker_required
def user_dashboard(request):
    """
    User dashboard - same as admin but with restrictions.

    Args:
        request: Django request object.

    Returns:
        HttpResponse.
    """
    user = get_current_user(request)

    recent_games, available_games = _get_dashboard_context_data(user)

    context = {
        'recent_games': recent_games,
        'available_games': available_games,
        'is_user': True,  # Flag to indicate this is a user view, not admin
        'user': user
    }

    return render(request, 'SaveNLoad/dashboard.html', context)


@login_required
def worker_required(request):
    """
    Worker-required landing page when no client worker is connected.

    Args:
        request: Django request object.

    Returns:
        HttpResponse.
    """
    user = get_current_user(request)
    worker_ids = get_user_workers(user.id)
    if worker_ids:
        target = 'admin:dashboard' if user.is_admin() else 'user:dashboard'
        return redirect(reverse(target))

    unpaired_workers = get_workers_snapshot()
    return render(request, 'SaveNLoad/worker_required.html', {
        'unpaired_workers': unpaired_workers
    })


@login_required
@require_http_methods(["GET"])
def search_available_games(request):
    """
    AJAX endpoint to search and sort available games.

    Args:
        request: Django request object.

    Returns:
        JsonResponse with game list.
    """
    user = get_current_user(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    # Get and sanitize query parameters
    from SaveNLoad.views.input_sanitizer import sanitize_search_query
    raw_search_query = request.GET.get('q', '').strip()
    search_query = sanitize_search_query(raw_search_query) if raw_search_query else None
    sort_by = request.GET.get('sort', 'name_asc')  # Default: name ascending

    # Start with annotated games to get efficient last_played access
    db_games = _get_annotated_games(user)

    # Apply search filter if provided
    if search_query:
        # Case-insensitive containment test
        db_games = db_games.filter(name__icontains=search_query)

    # Apply DB-side sorting
    # This is much more efficient than fetching all and sorting in Python
    if sort_by == 'name_desc':
        db_games = db_games.order_by(Lower('name').desc(), 'id')
    elif sort_by == 'last_saved_desc':
        # Sort by user_last_played (newest first).
        # Filter out games that have never been played (no last_played_timestamp) per user request
        db_games = db_games.filter(user_last_played__isnull=False).order_by(F('user_last_played').desc(), Lower('name'))
    elif sort_by == 'last_saved_asc':
        # Sort by user_last_played (oldest first). 
        # Filter out games that have never been played (no last_played_timestamp) per user request
        db_games = db_games.filter(user_last_played__isnull=False).order_by(F('user_last_played').asc(), Lower('name'))
    else:  # name_asc or invalid
        db_games = db_games.order_by(Lower('name'), 'id')

    # Build games list with last_played data
    games_list = []

    # Execute query
    for game in db_games:
        last_played = game.user_last_played
        save_locations = get_game_save_locations(game)
        games_list.append({
            'id': game.id,
            'title': game.name,
            'image': get_image_url_or_fallback(game),
            'footer': format_last_played(last_played),
            'last_played_timestamp': last_played.isoformat() if last_played else None,
            'save_file_locations': save_locations,
            'save_file_locations_json': json.dumps(save_locations),
        })

    return JsonResponse({
        'success': True,
        'games': games_list,
        'count': len(games_list)
    })
