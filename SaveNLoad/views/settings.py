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
import logging

logger = logging.getLogger(__name__)


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
def update_account_settings(request):
    """Update account settings (email and/or password)"""
    user = get_current_user(request)
    if not user:
        return json_response_error('Unauthorized', status=403)
    
    data, error_response = parse_json_body(request)
    if error_response:
        return error_response
    
    # Sanitize inputs
    from SaveNLoad.views.input_sanitizer import sanitize_email, validate_password_strength
    import re
    
    # Sanitize email
    raw_email = data.get('email', '').strip()
    email = sanitize_email(raw_email) if raw_email else None
    
    # If email was provided but sanitization failed, it's invalid
    if raw_email and not email:
        return json_response_error('Invalid email format.', status=400)
    
    # Sanitize password inputs (strip whitespace, validate length, but don't escape - will be hashed)
    current_password = data.get('current_password', '').strip()
    new_password = data.get('new_password', '').strip()
    confirm_password = data.get('confirm_password', '').strip()
    
    # Validate password length (prevent extremely long inputs that could cause issues)
    if current_password and len(current_password) > 128:
        return json_response_error('Password is too long (maximum 128 characters).', status=400)
    if new_password and len(new_password) > 128:
        return json_response_error('Password is too long (maximum 128 characters).', status=400)
    if confirm_password and len(confirm_password) > 128:
        return json_response_error('Password is too long (maximum 128 characters).', status=400)
    
    # Check for null bytes or other dangerous characters in passwords
    if current_password and '\x00' in current_password:
        return json_response_error('Invalid characters in password.', status=400)
    if new_password and '\x00' in new_password:
        return json_response_error('Invalid characters in password.', status=400)
    if confirm_password and '\x00' in confirm_password:
        return json_response_error('Invalid characters in password.', status=400)
    
    messages = []
    email_changed = False
    password_changed = False
    
    # Handle email change (email-only updates are allowed)
    if email:
        # Email is already sanitized and validated by sanitize_email
        if email.lower() != user.email.lower():
            # Check if email is already taken
            from SaveNLoad.models import SimpleUsers
            if SimpleUsers.objects.filter(email__iexact=email).exclude(id=user.id).exists():
                return json_response_error('This email is already in use by another account.', status=400)
            
            user.email = email
            email_changed = True
            messages.append('Email updated successfully')
    
    # Handle password change (only if password fields are provided - password change is optional)
    if current_password or new_password or confirm_password:
        # All password fields must be provided
        if not current_password:
            return json_response_error('Current password is required to change password.', status=400)
        
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
        
        # Validate password strength (already imported above)
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            return json_response_error(error_msg, status=400)
        
        # Check if new password is different from current
        if user.check_password(new_password):
            return json_response_error('New password must be different from current password.', status=400)
        
        # Update password
        user.set_password(new_password)
        password_changed = True
        messages.append('Password changed successfully')
    
    # Save if anything changed
    if email_changed or password_changed:
        user.save()
        message = ' and '.join(messages) + '!'
        return json_response_success(message=message)
    else:
        return json_response_success(message='No changes made.')


@login_required
@require_http_methods(["GET"])
def operation_queue_stats(request):
    """Get statistics about the operation queue (Admin only)"""
    user = get_current_user(request)
    error_response = check_admin_or_error(user)
    if error_response:
        return error_response
    
    from SaveNLoad.models.operation_queue import OperationQueue, OperationStatus, OperationType
    from django.utils import timezone
    from datetime import timedelta
    
    # Get all operations
    all_operations = OperationQueue.objects.all()
    total_count = all_operations.count()
    
    # Count by status
    status_counts = {}
    for status_code, status_label in OperationStatus.CHOICES:
        status_counts[status_code] = all_operations.filter(status=status_code).count()
    
    # Count by type
    type_counts = {}
    for type_code, type_label in OperationType.CHOICES:
        type_counts[type_code] = all_operations.filter(operation_type=type_code).count()
    
    # Get oldest and newest operations
    oldest = all_operations.order_by('created_at').first()
    newest = all_operations.order_by('-created_at').first()
    
    # Count operations older than 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    old_count = all_operations.filter(created_at__lt=thirty_days_ago).count()
    
    # Count operations older than 7 days
    seven_days_ago = timezone.now() - timedelta(days=7)
    week_old_count = all_operations.filter(created_at__lt=seven_days_ago).count()
    
    # Count stuck operations (in progress for more than 1 hour)
    one_hour_ago = timezone.now() - timedelta(hours=1)
    stuck_count = all_operations.filter(
        status=OperationStatus.IN_PROGRESS,
        started_at__lt=one_hour_ago
    ).count()
    
    stats = {
        'total': total_count,
        'by_status': {
            'pending': status_counts.get(OperationStatus.PENDING, 0),
            'in_progress': status_counts.get(OperationStatus.IN_PROGRESS, 0),
            'completed': status_counts.get(OperationStatus.COMPLETED, 0),
            'failed': status_counts.get(OperationStatus.FAILED, 0),
        },
        'by_type': {
            'save': type_counts.get(OperationType.SAVE, 0),
            'load': type_counts.get(OperationType.LOAD, 0),
            'list': type_counts.get(OperationType.LIST, 0),
            'delete': type_counts.get(OperationType.DELETE, 0),
        },
        'oldest_operation': oldest.created_at.isoformat() if oldest else None,
        'newest_operation': newest.created_at.isoformat() if newest else None,
        'old_count_30_days': old_count,
        'old_count_7_days': week_old_count,
        'stuck_count': stuck_count,
    }
    
    return json_response_success(data=stats)


@login_required
@require_http_methods(["POST"])
def operation_queue_cleanup(request):
    """Cleanup operation queue (Admin only)"""
    user = get_current_user(request)
    error_response = check_admin_or_error(user)
    if error_response:
        return error_response
    
    from SaveNLoad.models.operation_queue import OperationQueue, OperationStatus
    from django.utils import timezone
    from datetime import timedelta
    
    data, error_response = parse_json_body(request)
    if error_response:
        return error_response
    
    cleanup_type = data.get('type', '').strip()
    
    # CRITICAL SAFETY: Only delete OperationQueue records - this does NOT affect:
    # - SaveFolder records (completely independent model, no relationship)
    # - Game.last_played (separate field on Game model)
    # - FTP files (operations are just queue records, not the actual saves)
    # - Any other models
    # The ForeignKey CASCADE only works one way: deleting a Game/User deletes operations, NOT the reverse
    # OperationQueue and SaveFolder are completely independent - no ForeignKey between them
    
    if cleanup_type == 'completed':
        # Delete all completed operations - ONLY OperationQueue records
        deleted_count, deleted_objects = OperationQueue.objects.filter(status=OperationStatus.COMPLETED).delete()
        # Verify only OperationQueue was deleted (safety check)
        if 'SaveNLoad.OperationQueue' not in deleted_objects or len(deleted_objects) > 1:
            logger.warning(f"Unexpected objects deleted: {deleted_objects}")
        return json_response_success(
            message=f'Deleted {deleted_count} completed operation(s)',
            data={'deleted_count': deleted_count}
        )
    
    elif cleanup_type == 'failed':
        # Delete all failed operations - ONLY OperationQueue records
        deleted_count, deleted_objects = OperationQueue.objects.filter(status=OperationStatus.FAILED).delete()
        if 'SaveNLoad.OperationQueue' not in deleted_objects or len(deleted_objects) > 1:
            logger.warning(f"Unexpected objects deleted: {deleted_objects}")
        return json_response_success(
            message=f'Deleted {deleted_count} failed operation(s)',
            data={'deleted_count': deleted_count}
        )
    
    elif cleanup_type == 'old':
        # Delete operations older than 30 days - ONLY OperationQueue records
        thirty_days_ago = timezone.now() - timedelta(days=30)
        deleted_count, deleted_objects = OperationQueue.objects.filter(created_at__lt=thirty_days_ago).delete()
        if 'SaveNLoad.OperationQueue' not in deleted_objects or len(deleted_objects) > 1:
            logger.warning(f"Unexpected objects deleted: {deleted_objects}")
        return json_response_success(
            message=f'Deleted {deleted_count} old operation(s) (30+ days)',
            data={'deleted_count': deleted_count}
        )
    
    elif cleanup_type == 'all':
        # Delete all operations - ONLY OperationQueue records
        deleted_count, deleted_objects = OperationQueue.objects.all().delete()
        # Safety check: verify only OperationQueue was deleted
        if 'SaveNLoad.OperationQueue' not in deleted_objects or len(deleted_objects) > 1:
            logger.error(f"CRITICAL: Unexpected objects deleted during cleanup: {deleted_objects}")
            return json_response_error(
                f'Cleanup deleted unexpected objects: {deleted_objects}. Aborted to prevent data loss.',
                status=500
            )
        return json_response_success(
            message=f'Deleted all {deleted_count} operation(s)',
            data={'deleted_count': deleted_count}
        )
    
    else:
        return json_response_error('Invalid cleanup type. Must be: completed, failed, old, or all', status=400)