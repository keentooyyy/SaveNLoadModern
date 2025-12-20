from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.db.models import Max
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from datetime import timedelta
from SaveNLoad.views.custom_decorators import login_required, get_current_user, client_worker_required
from SaveNLoad.views.api_helpers import check_admin_or_error, json_response_success
from SaveNLoad.views.rawg_api import get_popular_games
from SaveNLoad.models import SimpleUsers, Game
from SaveNLoad.models.operation_queue import OperationQueue, OperationType, OperationStatus
from SaveNLoad.models.save_folder import SaveFolder


def format_last_played(last_played):
    """Format last_played datetime as a human-readable string"""
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


@login_required
@client_worker_required
def admin_dashboard(request):
    """Admin dashboard"""
    user = get_current_user(request)
    error_response = check_admin_or_error(user)
    if error_response:
        # Redirect non-admin users to their dashboard
        return redirect(reverse('user:dashboard'))
    
    # Get user's most recent game plays from SaveFolder records
    # This is more reliable than OperationQueue since SaveFolder persists even when operations are cleared
    # Get the most recent created_at per game for this user (created_at is updated when folder is reused)
    recent_save_folders = SaveFolder.objects.filter(
        user=user
    ).values('game').annotate(
        last_played=Max('created_at')
    ).order_by('-last_played')[:10]
    
    # Get game IDs and their last_played timestamps
    game_last_played = {sf['game']: sf['last_played'] for sf in recent_save_folders}
    
    # Fetch games ordered by user's last_played
    recent_db_games = Game.objects.filter(
        id__in=game_last_played.keys()
    )
    
    # Sort by last_played timestamp from save folders
    from SaveNLoad.utils.list_utils import sort_by_dict_lookup
    recent_db_games = sort_by_dict_lookup(recent_db_games, game_last_played, reverse=True)
    
    recent_games = []
    for game in recent_db_games:
        last_played = game_last_played.get(game.id)
        recent_games.append({
            'title': game.name,
            'image': game.banner if game.banner else '',
            'playtime': format_last_played(last_played),
        })
    
    # Fetch all games from database for available games section (sorted alphabetically)
    # Get per-user last_played for each game
    db_games = Game.objects.all().order_by('name', 'id')  # Add 'id' for stable sorting
    available_games = []
    
    # Get last_played for all games for this user from SaveFolder records
    # This persists even when operations are cleared
    all_user_save_folders = SaveFolder.objects.filter(
        user=user
    ).values('game').annotate(
        last_played=Max('created_at')
    )
    
    game_last_played_all = {sf['game']: sf['last_played'] for sf in all_user_save_folders}
    
    for game in db_games:
        last_played = game_last_played_all.get(game.id)
        available_games.append({
            'id': game.id,
            'title': game.name,
            'image': game.banner if game.banner else '',
            'footer': format_last_played(last_played),
        })
    
    # Sort available games case-insensitively by title (fixes default sorting bug)
    from SaveNLoad.utils.list_utils import sort_by_field
    available_games = sort_by_field(available_games, 'title', reverse=False, case_insensitive=True)
    
    context = {
        'recent_games': recent_games,
        'available_games': available_games,
        'user': user
    }
    
    return render(request, 'SaveNLoad/admin/dashboard.html', context)


@login_required
@client_worker_required
def user_dashboard(request):
    """User dashboard - same as admin but with restrictions"""
    user = get_current_user(request)
    
    # Get user's most recent game plays from SaveFolder records
    # This is more reliable than OperationQueue since SaveFolder persists even when operations are cleared
    # Get the most recent created_at per game for this user (created_at is updated when folder is reused)
    recent_save_folders = SaveFolder.objects.filter(
        user=user
    ).values('game').annotate(
        last_played=Max('created_at')
    ).order_by('-last_played')[:10]
    
    # Get game IDs and their last_played timestamps
    game_last_played = {sf['game']: sf['last_played'] for sf in recent_save_folders}
    
    # Fetch games ordered by user's last_played
    recent_db_games = Game.objects.filter(
        id__in=game_last_played.keys()
    )
    
    # Sort by last_played timestamp from save folders
    from SaveNLoad.utils.list_utils import sort_by_dict_lookup
    recent_db_games = sort_by_dict_lookup(recent_db_games, game_last_played, reverse=True)
    
    recent_games = []
    for game in recent_db_games:
        last_played = game_last_played.get(game.id)
        recent_games.append({
            'title': game.name,
            'image': game.banner if game.banner else '',
            'playtime': format_last_played(last_played),
        })
    
    # Fetch all games from database for available games section (sorted alphabetically)
    # Get per-user last_played for each game
    db_games = Game.objects.all().order_by('name', 'id')  # Add 'id' for stable sorting
    available_games = []
    
    # Get last_played for all games for this user from SaveFolder records
    # This persists even when operations are cleared
    all_user_save_folders = SaveFolder.objects.filter(
        user=user
    ).values('game').annotate(
        last_played=Max('created_at')
    )
    
    game_last_played_all = {sf['game']: sf['last_played'] for sf in all_user_save_folders}
    
    for game in db_games:
        last_played = game_last_played_all.get(game.id)
        available_games.append({
            'id': game.id,
            'title': game.name,
            'image': game.banner if game.banner else '',
            'footer': format_last_played(last_played),
        })
    
    # Sort available games case-insensitively by title (fixes default sorting bug)
    from SaveNLoad.utils.list_utils import sort_by_field
    available_games = sort_by_field(available_games, 'title', reverse=False, case_insensitive=True)
    
    context = {
        'recent_games': recent_games,
        'available_games': available_games,
        'is_user': True,  # Flag to indicate this is a user view, not admin
        'user': user
    }
    
    return render(request, 'SaveNLoad/user/dashboard.html', context)


@login_required
@require_http_methods(["GET"])
def search_available_games(request):
    """AJAX endpoint to search and sort available games"""
    user = get_current_user(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    # Get and sanitize query parameters
    from SaveNLoad.views.input_sanitizer import sanitize_search_query
    raw_search_query = request.GET.get('q', '').strip()
    search_query = sanitize_search_query(raw_search_query) if raw_search_query else None
    sort_by = request.GET.get('sort', 'name_asc')  # Default: name ascending
    
    # Validate sort_by parameter (prevent injection)
    valid_sorts = ['name_asc', 'name_desc', 'last_saved_asc', 'last_saved_desc']
    if sort_by not in valid_sorts:
        sort_by = 'name_asc'
    
    # Fetch all games with consistent default ordering (by name, then ID for stability)
    db_games = Game.objects.all().order_by('name', 'id')
    
    # Apply search filter if provided
    if search_query:
        db_games = db_games.filter(name__icontains=search_query)
    
    # Get last_played for all games for this user from SaveFolder records
    # This persists even when operations are cleared
    all_user_save_folders = SaveFolder.objects.filter(
        user=user
    ).values('game').annotate(
        last_played=Max('created_at')
    )
    
    game_last_played_all = {sf['game']: sf['last_played'] for sf in all_user_save_folders}
    
    # Build games list with last_played data
    games_list = []
    for game in db_games:
        last_played = game_last_played_all.get(game.id)
        games_list.append({
            'id': game.id,
            'title': game.name,
            'image': game.banner if game.banner else '',
            'footer': format_last_played(last_played),
            'last_played_timestamp': last_played.isoformat() if last_played else None,
        })
    
    # Apply sorting
    from SaveNLoad.utils.list_utils import sort_by_field, filter_none_values
    if sort_by == 'name_asc':
        games_list = sort_by_field(games_list, 'title', reverse=False, case_insensitive=True)
    elif sort_by == 'name_desc':
        games_list = sort_by_field(games_list, 'title', reverse=True, case_insensitive=True)
    elif sort_by == 'last_saved_desc':
        # Filter out games that have never been played (no last_played_timestamp)
        games_list = filter_none_values(games_list, 'last_played_timestamp')
        # Sort by timestamp (most recent first)
        games_list = sort_by_field(games_list, 'last_played_timestamp', reverse=True)
    elif sort_by == 'last_saved_asc':
        # Filter out games that have never been played (no last_played_timestamp)
        games_list = filter_none_values(games_list, 'last_played_timestamp')
        # Sort by timestamp (oldest first)
        games_list = sort_by_field(games_list, 'last_played_timestamp', reverse=False)
    
    return JsonResponse({
        'success': True,
        'games': games_list,
        'count': len(games_list)
    })

