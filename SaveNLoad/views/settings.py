from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from SaveNLoad.views.custom_decorators import login_required, get_current_user, client_worker_required
from SaveNLoad.views.api_helpers import (
    parse_json_body,
    get_game_or_error,
    check_admin_or_error,
    json_response_error,
    json_response_success
)
from SaveNLoad.views.rawg_api import search_games as rawg_search_games
from SaveNLoad.models import Game
import json


@login_required
@client_worker_required
def settings_view(request):
    """Settings page for managing games (Admin only)"""
    user = get_current_user(request)
    error_response = check_admin_or_error(user)
    if error_response:
        # Redirect non-admin users to their dashboard
        return redirect(reverse('user:dashboard'))
    
    context = {
        'user': user
    }
    return render(request, 'SaveNLoad/admin/settings.html', context)


@login_required
@client_worker_required
def user_settings_view(request):
    """Settings page for users (without add game functionality)"""
    user = get_current_user(request)
    context = {
        'is_user': True,
        'user': user
    }
    return render(request, 'SaveNLoad/user/settings.html', context)


@login_required
@client_worker_required
@require_http_methods(["POST"])
def create_game(request):
    """Create a new game (AJAX endpoint - Admin only)"""
    user = get_current_user(request)
    error_response = check_admin_or_error(user)
    if error_response:
        return error_response
    
    # Handle both form data and JSON
    if request.headers.get('Content-Type') == 'application/json':
        data, error_response = parse_json_body(request)
        if error_response:
            return error_response
        name = (data.get('name') or '').strip()
        save_file_location = (data.get('save_file_location') or '').strip()
        banner = (data.get('banner') or '').strip()
    else:
        name = request.POST.get('name', '').strip()
        save_file_location = request.POST.get('save_file_location', '').strip()
        banner = request.POST.get('banner', '').strip()
    
    if not name or not save_file_location:
        return json_response_error('Game name and save file location are required.', status=400)
    
    # Check if game with same name already exists
    if Game.objects.filter(name=name).exists():
        return json_response_error('A game with this name already exists.', status=400)
    
    # Create new game
    game_data = {
        'name': name,
        'save_file_location': save_file_location,
    }
    if banner:
        game_data['banner'] = banner
    
    game = Game.objects.create(**game_data)
    
    return json_response_success(
        message=f'Game "{game.name}" created successfully!',
        data={
            'game': {
                'id': game.id,
                'name': game.name,
                'banner': game.banner or '',
                'save_file_location': game.save_file_location,
            }
        }
    )


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
    error_response = check_admin_or_error(user)
    if error_response:
        return error_response

    # Get game or return error
    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response

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
        return json_response_success()

    # POST - update
    data, error_response = parse_json_body(request)
    if error_response:
        return error_response

    name = (data.get('name') or '').strip()
    save_file_location = (data.get('save_file_location') or '').strip()
    banner = (data.get('banner') or '').strip()

    if not name or not save_file_location:
        return json_response_error('Game name and save file location are required.', status=400)

    # Ensure unique name (excluding this game)
    if Game.objects.exclude(pk=game.id).filter(name=name).exists():
        return json_response_error('A game with this name already exists.', status=400)

    game.name = name
    game.save_file_location = save_file_location
    game.banner = banner or None
    game.save()

    return json_response_success(
        data={
            'game': {
                'id': game.id,
                'name': game.name,
                'banner': game.banner or '',
                'save_file_location': game.save_file_location,
            }
        }
    )


@login_required
@require_http_methods(["POST"])
def delete_game(request, game_id):
    """Dedicated delete endpoint (alias for DELETE for clients that prefer POST)."""
    user = get_current_user(request)
    error_response = check_admin_or_error(user)
    if error_response:
        return error_response

    # Get game or return error
    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response

    game.delete()
    return json_response_success()


@login_required
@require_http_methods(["POST"])
def change_password(request):
    """Change user password"""
    user = get_current_user(request)
    if not user:
        return json_response_error('Unauthorized', status=403)
    
    data, error_response = parse_json_body(request)
    if error_response:
        return error_response
    
    current_password = data.get('current_password', '').strip()
    new_password = data.get('new_password', '').strip()
    confirm_password = data.get('confirm_password', '').strip()
    
    # Validate inputs
    if not current_password:
        return json_response_error('Current password is required.', status=400)
    
    if not new_password:
        return json_response_error('New password is required.', status=400)
    
    if not confirm_password:
        return json_response_error('Please confirm your new password.', status=400)
    
    # Check current password
    if not user.check_password(current_password):
        return json_response_error('Current password is incorrect.', status=400)
    
    # Validate new password matches confirmation
    if new_password != confirm_password:
        return json_response_error('New passwords do not match.', status=400)
    
    # Validate password strength
    from SaveNLoad.views.input_sanitizer import validate_password_strength
    is_valid, error_msg = validate_password_strength(new_password)
    if not is_valid:
        return json_response_error(error_msg, status=400)
    
    # Check if new password is different from current
    if user.check_password(new_password):
        return json_response_error('New password must be different from current password.', status=400)
    
    # Update password
    user.set_password(new_password)
    user.save()
    
    return json_response_success(message='Password changed successfully!')

