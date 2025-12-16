from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from SaveNLoad.views.custom_decorators import login_required, get_current_user, client_worker_required
from SaveNLoad.views.rawg_api import get_popular_games
from SaveNLoad.models import SimpleUsers, Game


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
    if not user or not user.is_admin():
        # Redirect non-admin users to their dashboard
        return redirect(reverse('user:dashboard'))
    
    # Fetch games from database ordered by last_played (most recent first)
    # Only show games that have been played at least once
    recent_db_games = Game.objects.filter(
        last_played__isnull=False
    ).order_by('-last_played')[:10]
    
    recent_games = []
    for game in recent_db_games:
        recent_games.append({
            'title': game.name,
            'image': game.banner if game.banner else '',
            'playtime': format_last_played(game.last_played),
        })
    
    # Fetch all games from database for available games section (sorted alphabetically)
    db_games = Game.objects.all().order_by('name')
    available_games = []
    for game in db_games:
        available_games.append({
            'id': game.id,
            'title': game.name,
            'image': game.banner if game.banner else '',
            'footer': format_last_played(game.last_played),
        })
    
    context = {
        'recent_games': recent_games,
        'available_games': available_games
    }
    
    return render(request, 'SaveNLoad/admin/dashboard.html', context)


@login_required
@client_worker_required
def user_dashboard(request):
    """User dashboard"""
    return render(request, 'SaveNLoad/user/dashboard.html')

