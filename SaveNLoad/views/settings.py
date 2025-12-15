from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from .custom_decorators import login_required, get_current_user
from .rawg_api import search_games as rawg_search_games
from ..models import Game
import json


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


@login_required
@require_http_methods(["GET", "POST", "DELETE"])
def game_detail(request, game_id):
    """Get, update, or delete a single Game (admin only, AJAX)."""
    user = get_current_user(request)
    if not user or not user.is_admin():
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return JsonResponse({'error': 'Game not found'}, status=404)

    if request.method == "GET":
        return JsonResponse({
            'id': game.id,
            'name': game.name,
            'banner': game.banner or '',
            'save_file_location': game.save_file_location,
            'last_played': game.last_played.isoformat() if getattr(game, "last_played", None) else None,
        })

    if request.method == "DELETE":
        game.delete()
        return JsonResponse({'success': True})

    # POST - update
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    name = (data.get('name') or '').strip()
    save_file_location = (data.get('save_file_location') or '').strip()
    banner = (data.get('banner') or '').strip()

    if not name or not save_file_location:
        return JsonResponse({'error': 'Game name and save file location are required.'}, status=400)

    # Ensure unique name (excluding this game)
    if Game.objects.exclude(pk=game.id).filter(name=name).exists():
        return JsonResponse({'error': 'A game with this name already exists.'}, status=400)

    game.name = name
    game.save_file_location = save_file_location
    game.banner = banner or None
    game.save()

    return JsonResponse({
        'success': True,
        'game': {
            'id': game.id,
            'name': game.name,
            'banner': game.banner or '',
            'save_file_location': game.save_file_location,
        }
    })


@login_required
@require_http_methods(["POST"])
def delete_game(request, game_id):
    """Dedicated delete endpoint (alias for DELETE for clients that prefer POST)."""
    user = get_current_user(request)
    if not user or not user.is_admin():
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return JsonResponse({'error': 'Game not found'}, status=404)

    game.delete()
    return JsonResponse({'success': True})

