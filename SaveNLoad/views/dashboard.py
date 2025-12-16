from django.shortcuts import render, redirect
from django.urls import reverse
from SaveNLoad.views.custom_decorators import login_required, get_current_user
from SaveNLoad.views.rawg_api import get_popular_games
from SaveNLoad.models import SimpleUsers, Game


def get_playtime_strings():
    """Get ordered playtime strings from most recent to oldest"""
    return [
        "Last played 3 mins ago",
        "Last played 1 hour ago",
        "Last played 2 hours ago",
        "Last played 5 hours ago",
        "Last played 1 day ago",
        "Last played 2 days ago",
        "Last played 3 days ago",
        "Last played 1 week ago",
        "Last played 2 weeks ago",
        "Last played 3 weeks ago",
    ]


@login_required
def admin_dashboard(request):
    """Admin dashboard"""
    from SaveNLoad.models.client_worker import ClientWorker
    
    user = get_current_user(request)
    if not user or not user.is_admin():
        # Redirect non-admin users to their dashboard
        return redirect(reverse('user:dashboard'))
    
    # Check if client worker is connected
    if not ClientWorker.is_worker_connected():
        return redirect(reverse('SaveNLoad:worker_required'))
    
    # Fetch real games from RAWG API
    games = get_popular_games(limit=10)
    
    # Get ordered playtime strings (most recent to oldest)
    playtime_strings = get_playtime_strings()
    
    # Add fake playtime to each game in order (most recent first)
    games_with_playtime = []
    for index, game in enumerate(games):
        # Assign playtime based on index (first game = most recent)
        playtime = playtime_strings[index] if index < len(playtime_strings) else playtime_strings[-1]
        games_with_playtime.append({
            'title': game['title'],
            'image': game['image'],
            'playtime': playtime
        })
    
    # Fetch games from database (user-added games)
    db_games = Game.objects.all().order_by('-created_at')[:10]
    available_games = []
    for game in db_games:
        available_games.append({
            'id': game.id,
            'title': game.name,
            'image': game.banner if game.banner else '',
            'footer': game.save_file_location,
        })
    
    # Games are already sorted by recency (most recent first)
    context = {
        'recent_games': games_with_playtime,
        'available_games': available_games
    }
    
    return render(request, 'SaveNLoad/admin/dashboard.html', context)


@login_required
def user_dashboard(request):
    """User dashboard"""
    return render(request, 'SaveNLoad/user/dashboard.html')

