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
    
    # Get user's most recent game plays from completed save operations
    # Get the most recent completed_at per game for this user
    recent_operations = OperationQueue.objects.filter(
        user=user,
        operation_type=OperationType.SAVE,
        status=OperationStatus.COMPLETED,
        completed_at__isnull=False
    ).values('game').annotate(
        last_played=Max('completed_at')
    ).order_by('-last_played')[:10]
    
    # Get game IDs and their last_played timestamps
    game_last_played = {op['game']: op['last_played'] for op in recent_operations}
    
    # Fetch games ordered by user's last_played
    recent_db_games = Game.objects.filter(
        id__in=game_last_played.keys()
    )
    
    # Sort by last_played timestamp from operations
    recent_db_games = sorted(recent_db_games, key=lambda g: game_last_played.get(g.id), reverse=True)
    
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
    db_games = Game.objects.all().order_by('name')
    available_games = []
    
    # Get last_played for all games for this user
    all_user_operations = OperationQueue.objects.filter(
        user=user,
        operation_type=OperationType.SAVE,
        status=OperationStatus.COMPLETED,
        completed_at__isnull=False
    ).values('game').annotate(
        last_played=Max('completed_at')
    )
    
    game_last_played_all = {op['game']: op['last_played'] for op in all_user_operations}
    
    for game in db_games:
        last_played = game_last_played_all.get(game.id)
        available_games.append({
            'id': game.id,
            'title': game.name,
            'image': game.banner if game.banner else '',
            'footer': format_last_played(last_played),
        })
    
    context = {
        'recent_games': recent_games,
        'available_games': available_games
    }
    
    return render(request, 'SaveNLoad/admin/dashboard.html', context)


@login_required
@client_worker_required
def user_dashboard(request):
    """User dashboard - same as admin but with restrictions"""
    user = get_current_user(request)
    
    # Get user's most recent game plays from completed save operations
    # Get the most recent completed_at per game for this user
    recent_operations = OperationQueue.objects.filter(
        user=user,
        operation_type=OperationType.SAVE,
        status=OperationStatus.COMPLETED,
        completed_at__isnull=False
    ).values('game').annotate(
        last_played=Max('completed_at')
    ).order_by('-last_played')[:10]
    
    # Get game IDs and their last_played timestamps
    game_last_played = {op['game']: op['last_played'] for op in recent_operations}
    
    # Fetch games ordered by user's last_played
    recent_db_games = Game.objects.filter(
        id__in=game_last_played.keys()
    )
    
    # Sort by last_played timestamp from operations
    recent_db_games = sorted(recent_db_games, key=lambda g: game_last_played.get(g.id), reverse=True)
    
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
    db_games = Game.objects.all().order_by('name')
    available_games = []
    
    # Get last_played for all games for this user
    all_user_operations = OperationQueue.objects.filter(
        user=user,
        operation_type=OperationType.SAVE,
        status=OperationStatus.COMPLETED,
        completed_at__isnull=False
    ).values('game').annotate(
        last_played=Max('completed_at')
    )
    
    game_last_played_all = {op['game']: op['last_played'] for op in all_user_operations}
    
    for game in db_games:
        last_played = game_last_played_all.get(game.id)
        available_games.append({
            'id': game.id,
            'title': game.name,
            'image': game.banner if game.banner else '',
            'footer': format_last_played(last_played),
        })
    
    context = {
        'recent_games': recent_games,
        'available_games': available_games,
        'is_user': True  # Flag to indicate this is a user view, not admin
    }
    
    return render(request, 'SaveNLoad/user/dashboard.html', context)


@login_required
@require_http_methods(["GET"])
def search_available_games(request):
    """AJAX endpoint to search and sort available games"""
    user = get_current_user(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    # Get query parameters
    search_query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'name_asc')  # Default: name ascending
    
    # Fetch all games
    db_games = Game.objects.all()
    
    # Apply search filter if provided
    if search_query:
        db_games = db_games.filter(name__icontains=search_query)
    
    # Get last_played for all games for this user
    all_user_operations = OperationQueue.objects.filter(
        user=user,
        operation_type=OperationType.SAVE,
        status=OperationStatus.COMPLETED,
        completed_at__isnull=False
    ).values('game').annotate(
        last_played=Max('completed_at')
    )
    
    game_last_played_all = {op['game']: op['last_played'] for op in all_user_operations}
    
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
    if sort_by == 'name_asc':
        games_list.sort(key=lambda x: x['title'].lower())
    elif sort_by == 'name_desc':
        games_list.sort(key=lambda x: x['title'].lower(), reverse=True)
    elif sort_by == 'last_saved_desc':
        # Most recent first (games with saves first, then games without saves)
        games_list.sort(key=lambda x: (
            x['last_played_timestamp'] is None,  # Games without saves go to end
            x['last_played_timestamp'] or ''  # Then sort by timestamp (most recent first)
        ), reverse=True)
    elif sort_by == 'last_saved_asc':
        # Oldest first (games with saves first, then games without saves)
        # Convert timestamp to comparable value - None goes to end
        games_list.sort(key=lambda x: (
            x['last_played_timestamp'] is None,  # Games without saves go to end
            x['last_played_timestamp'] if x['last_played_timestamp'] else '9999-12-31'  # Oldest first (ascending)
        ))
    
    return JsonResponse({
        'success': True,
        'games': games_list,
        'count': len(games_list)
    })

