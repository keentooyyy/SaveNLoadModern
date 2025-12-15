from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from .custom_decorators import login_required, get_current_user
from .rawg_api import search_games as rawg_search_games
from ..models import Game


@login_required
def settings_view(request):
    """Settings page for managing games (Admin only)"""
    user = get_current_user(request)
    if not user or not user.is_admin():
        # Redirect non-admin users to their dashboard
        return redirect(reverse('user:dashboard'))
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        save_file_location = request.POST.get('save_file_location', '').strip()
        banner = request.POST.get('banner', '').strip()
        
        if not name or not save_file_location:
            return render(request, 'SaveNLoad/admin/settings.html', {
                'error': 'Game name and save file location are required.'
            })
        
        # Check if game with same name already exists
        if Game.objects.filter(name=name).exists():
            return render(request, 'SaveNLoad/admin/settings.html', {
                'error': 'A game with this name already exists.'
            })
        
        # Create new game
        game_data = {
            'name': name,
            'save_file_location': save_file_location,
        }
        if banner:
            game_data['banner'] = banner
        
        Game.objects.create(**game_data)
        
        return redirect('admin:settings')
    
    return render(request, 'SaveNLoad/admin/settings.html')


@login_required
@require_http_methods(["GET"])
def search_game(request):
    """Search RAWG for games by name (AJAX endpoint - Admin only)"""
    user = get_current_user(request)
    if not user or not user.is_admin():
        return JsonResponse({'games': []}, status=403)
    
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({'games': []})
    
    games = rawg_search_games(query=query, limit=10)
    
    results = []
    for game in games:
        results.append(
            {
                'id': game.get('id'),
                'name': game.get('title') or game.get('name') or 'Unknown',
                'banner': game.get('image') or '',
                # RAWG doesn't know the local save path – leave empty for manual input
                'save_file_location': '',
            }
        )
    
    return JsonResponse({'games': results})

