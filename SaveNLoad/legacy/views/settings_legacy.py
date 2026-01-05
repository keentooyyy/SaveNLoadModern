import os
from urllib.parse import urlparse

from django.core.files import File
from django.db import models
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from SaveNLoad.models import Game
from SaveNLoad.utils.image_utils import download_image_from_url, get_image_url_or_fallback
from SaveNLoad.views.api_helpers import (
    parse_json_body,
    get_game_or_error,
    check_admin_or_error,
    json_response_error,
    json_response_success,
    delete_game_banner_file,
    normalize_save_file_locations,
    validate_unique_save_file_locations,
    cleanup_operations_by_status,
    cleanup_operations_by_age
)
from SaveNLoad.views.custom_decorators import login_required, get_current_user, client_worker_required
from SaveNLoad.views.rawg_api import search_games as rawg_search_games


@login_required
@client_worker_required
def settings_view(request):
    """
    Settings page for managing games (Admin only).

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

    context = {
        'is_user': False,  # Add this line
        'user': user
    }
    return render(request, 'SaveNLoad/settings.html', context)


@login_required
@client_worker_required
def user_settings_view(request):
    """
    Settings page for users (without add game functionality).

    Args:
        request: Django request object.

    Returns:
        HttpResponse.
    """
    user = get_current_user(request)
    context = {
        'is_user': True,
        'user': user
    }
    return render(request, 'SaveNLoad/settings.html', context)


@login_required
@require_http_methods(["POST"])
def create_game(request):
    """
    Create a new game (AJAX endpoint - Admin only).

    Args:
        request: Django request object.

    Returns:
        JsonResponse with created game data or error.
    """
    user = get_current_user(request)
    error_response = check_admin_or_error(user)
    if error_response:
        return error_response

    try:
        # Handle both form data and JSON
        if request.headers.get('Content-Type') == 'application/json':
            data, error_response = parse_json_body(request)
            if error_response:
                return error_response
            name = (data.get('name') or '').strip()
            # Support both single and multiple save locations
            save_file_locations = normalize_save_file_locations(data)
            banner = (data.get('banner') or '').strip()
        else:
            name = request.POST.get('name', '').strip()
            form_data = {
                'save_file_location': request.POST.get('save_file_location', '').strip(),
                'save_file_locations': request.POST.getlist('save_file_locations')
            }
            save_file_locations = normalize_save_file_locations(form_data)
            banner = request.POST.get('banner', '').strip()

        if not name or not save_file_locations:
            return json_response_error('Game name and at least one save file location are required.', status=400)

        if not save_file_locations:
            return json_response_error('At least one valid save file location is required.', status=400)

        duplicate_error = validate_unique_save_file_locations(save_file_locations)
        if duplicate_error:
            return duplicate_error

        # Check if game with same name already exists
        if Game.objects.filter(name=name).exists():
            return json_response_error('A game with this name already exists.', status=400)

        # Store locations as JSON array
        # Create new game
        game_data = {
            'name': name,
            'save_file_locations': save_file_locations,
        }

        # Store original URL
        if banner:
            game_data['banner_url'] = banner

        game = Game.objects.create(**game_data)

        # Generate path mappings if multiple paths
        game.generate_path_mappings()

        # Download and cache banner image (blocking - ensure it's cached)
        if banner:
            # Skip download if banner URL is from same server (localhost/local IP)
            from SaveNLoad.utils.image_utils import is_local_url
            if is_local_url(banner, request):
                # Local URL - skip download, just store the URL
                print(f"Banner URL is local ({banner}) - skipping download")
            else:
                # Download and cache banner (increased timeout for external URLs)
                try:
                    success, message, file_obj = download_image_from_url(banner, timeout=10)
                    if success and file_obj:
                        try:
                            # Determine file extension
                            parsed = urlparse(banner)
                            ext = os.path.splitext(parsed.path)[1] or '.jpg'
                            game.banner.save(f"banner_{game.id}{ext}", File(file_obj), save=True)
                            # Refresh game object to ensure banner field is updated
                            game.refresh_from_db()
                            # Update banner_url to local URL after successful download
                            if game.banner:
                                local_url = request.build_absolute_uri(game.banner.url) if request else game.banner.url
                                game.banner_url = local_url
                                game.save(update_fields=['banner_url'])
                            # Clean up temp file
                            if hasattr(file_obj, 'name'):
                                os.unlink(file_obj.name)
                            print(
                                f"Successfully downloaded and cached banner for game {game.id}: {game.banner.name if game.banner else 'NOT SET'}")
                        except Exception as e:
                            print(f"ERROR: Failed to save cached banner for game {game.id}: {e}")
                            # Continue - banner_url is already stored as fallback
                    else:
                        print(f"WARNING: Failed to download banner for game {game.id}: {message}")
                        # Continue - banner_url is already stored as fallback
                except Exception as e:
                    print(f"ERROR: Banner download failed for game {game.id}: {e}")
                    # Don't block the save operation - banner will load from URL

        return json_response_success(
            message=f'Game "{game.name}" created successfully!',
            data={
                'game': {
                    'id': game.id,
                    'name': game.name,
                    'banner': get_image_url_or_fallback(game, request),
                    'save_file_locations': game.save_file_locations,
                }
            }
        )
    except Exception as e:
        print(f"ERROR: Error creating game: {str(e)}")
        return json_response_error(f'Failed to create game: {str(e)}', status=500)


@login_required
@require_http_methods(["GET"])
def search_game(request):
    """
    Search RAWG for games by name (AJAX endpoint - Admin only).

    Args:
        request: Django request object.

    Returns:
        JsonResponse with game search results.
    """
    user = get_current_user(request)
    if not user or not user.is_admin():
        return JsonResponse({'games': []}, status=403)

    # Get and sanitize search query
    from SaveNLoad.views.input_sanitizer import sanitize_search_query
    raw_query = request.GET.get('q', '').strip()
    query = sanitize_search_query(raw_query) if raw_query else None

    if not query:
        return JsonResponse({'games': []})

    try:
        games = rawg_search_games(query=query, limit=15)

        results = []
        for game in games:
            results.append(
                {
                    'id': game.get('id'),
                    'name': game.get('title') or game.get('name') or 'Unknown',
                    'banner': game.get('image') or '',
                    # RAWG doesn't know the local save path – leave empty for manual input
                    'save_file_locations': [],
                    'year': game.get('year', ''),
                    'company': game.get('company', ''),
                }
            )

        return JsonResponse({'games': results})
    except Exception as e:
        print(f"ERROR: Error in search_game view: {e}")
        return JsonResponse({'games': [], 'error': 'Failed to search games'}, status=500)


def _queue_game_deletion_operations(game: Game, admin_user, request=None):
    """
    Queue operations to delete all FTP saves for a game before deletion.
    Creates delete operations for the entire game directory for each user who has saves.
    All operations are assigned to the admin's worker (the one making the delete request).
    
    Args:
        game: Game instance to delete
        admin_user: Admin user making the delete request (their worker will handle all deletions)
    
    Returns:
        tuple: (success: bool, error_message: str or None)
        - (True, None) if operations were queued successfully
        - (False, error_message) if FTP cleanup failed (no worker available, etc.)
    """
    from SaveNLoad.models.save_folder import SaveFolder
    from SaveNLoad.models.operation_constants import OperationType
    from SaveNLoad.services.redis_operation_service import create_operation

    try:
        # Get all save folders for this game (across all users)
        save_folders = SaveFolder.objects.filter(game=game)

        if not save_folders.exists():
            print(f"No save folders found for game {game.id} ({game.name}), no storage cleanup needed")
            # No saves to clean up, so we can return a special flag indicating immediate deletion is safe
            return (True, "no_saves")  # Special flag: no saves means immediate deletion is safe

        # Get unique users who have saves for this game
        users_with_saves = save_folders.values_list('user', flat=True).distinct()

        # Get the admin's worker (from session - automatic association)
        from SaveNLoad.views.api_helpers import get_client_worker_or_error
        client_worker, error_response = get_client_worker_or_error(admin_user, request)
        if error_response:
            error_msg = f"No active client worker available. Cannot delete remote saves for game '{game.name}'. Please ensure a client worker is running and try again."
            print(
                f"WARNING: No active client worker available for admin {admin_user.username}, cannot delete remote saves for game {game.id}")
            return (False, error_msg)

        # Build safe game name (same logic as SaveFolder._generate_remote_path)
        from SaveNLoad.utils.path_utils import sanitize_game_name
        safe_game_name = sanitize_game_name(game.name)

        # Create delete operations for each user's game directory
        # This will delete the entire game directory (username/gamename/) which includes all save folders
        # All operations are assigned to the admin's worker
        operations_created = 0
        for user_id in users_with_saves:
            from SaveNLoad.models.user import SimpleUsers
            try:
                user = SimpleUsers.objects.get(id=user_id)
                # Build the game directory path (username/gamename/)
                game_directory_path = f"{user.username}/{safe_game_name}"

                # Create DELETE operation for the entire game directory
                # Note: user field is the save owner, but operation is handled by admin's worker
                create_operation(
                    {
                        'operation_type': OperationType.DELETE,
                        'user_id': user.id,  # Save owner (for tracking)
                        'game_id': game.id,
                        'local_save_path': '',
                        'save_folder_number': None,  # Deleting entire game directory
                        'smb_path': game_directory_path,  # Full path to game directory
                        'path_index': None
                    },
                    client_worker  # Admin's worker handles all deletions
                )
                operations_created += 1
                print(
                    f"Queued delete operation for game directory: {game_directory_path} (assigned to admin's worker: {client_worker})")
            except Exception as e:
                print(f"ERROR: Failed to create delete operation for user {user_id}: {e}")
                return (False, f"Failed to queue storage cleanup operation: {str(e)}")

        if operations_created > 0:
            print(
                f"Queued {operations_created} delete operation(s) for game {game.id} ({game.name}) - all assigned to admin's worker")
            return (True, None)
        else:
            return (False, "Failed to create any storage cleanup operations")
    except Exception as e:
        error_msg = f"Error queueing game deletion operations: {str(e)}"
        print(f"ERROR: Error queueing game deletion operations for game {game.id}: {e}")
        return (False, error_msg)


def _handle_game_deletion(request, game, user):
    """
    Helper to handle game deletion logic
    Returns: JsonResponse

    Args:
        request: Django request object.
        game: Game instance to delete.
        user: Admin user requesting deletion.

    Returns:
        JsonResponse indicating queued or completed deletion.
    """
    # Queue operations to delete all remote saves for this game
    # Use admin's worker (the one making the delete request)
    # Do NOT delete game if storage cleanup fails to queue
    success, error_message = _queue_game_deletion_operations(game, admin_user=user, request=request)
    if not success:
        return json_response_error(error_message or "Failed to queue storage cleanup operations", status=503)

    # If no saves exist, delete immediately (nothing to clean up)
    if error_message == "no_saves":
        # Delete banner file before deleting game
        delete_game_banner_file(game)
        game.delete()
        print(f"Game {game.id} ({game.name}) deleted immediately - no remote saves to clean up")
    else:
        # Mark game for deletion - actual deletion happens after all storage cleanup operations complete successfully
        game.pending_deletion = True
        game.save()
        print(
            f"Game {game.id} ({game.name}) marked for deletion - will be deleted after all storage cleanup operations complete")
    return json_response_success()


@login_required
@require_http_methods(["GET", "POST", "DELETE"])
def game_detail(request, game_id):
    """
    Get, update, or delete a single Game (admin only, AJAX).

    Args:
        request: Django request object.
        game_id: Game identifier.

    Returns:
        JsonResponse with game data or operation status.
    """
    try:
        user = get_current_user(request)
        error_response = check_admin_or_error(user)
        if error_response:
            return error_response

        # Get game or return error
        game, error_response = get_game_or_error(game_id)
        if error_response:
            return error_response

        if request.method == "GET":
            from SaveNLoad.services.redis_operation_service import get_operations_by_game, OperationStatus
            from SaveNLoad.models.operation_constants import OperationType

            # Get deletion operations for this game (operations without save_folder_number)
            all_operations = get_operations_by_game(game.id)
            deletion_operations = [op for op in all_operations
                                   if op.get('type') == OperationType.DELETE and not op.get('save_folder_number')]

            # Get pending/in-progress operations
            from SaveNLoad.utils.operation_utils import get_pending_or_in_progress_operations
            pending_ops = get_pending_or_in_progress_operations(deletion_operations)
            total_deletion_ops = len(deletion_operations)
            pending_count = len(pending_ops)
            completed_count = len([op for op in deletion_operations if op.get('status') == OperationStatus.COMPLETED])
            failed_count = len([op for op in deletion_operations if op.get('status') == OperationStatus.FAILED])

            # Calculate progress percentage
            progress_percentage = 0
            if total_deletion_ops > 0:
                progress_percentage = int((completed_count / total_deletion_ops) * 100)

            return JsonResponse({
                'id': game.id,
                'name': game.name,
                'banner': get_image_url_or_fallback(game, request),  # Display URL for preview
                'banner_url': game.banner_url or '',  # Original URL for input field
                'save_file_locations': game.save_file_locations,
                'last_played': game.last_played.isoformat() if getattr(game, "last_played", None) else None,
                'pending_deletion': getattr(game, 'pending_deletion', False),
                'deletion_operations': {
                    'total': total_deletion_ops,
                    'pending': pending_count,
                    'completed': completed_count,
                    'failed': failed_count,
                    'progress_percentage': progress_percentage,
                }
            })

        if request.method == "DELETE":
            return _handle_game_deletion(request, game, user)

        # POST - update
        data, error_response = parse_json_body(request)
        if error_response:
            return error_response

        name = (data.get('name') or '').strip()
        # Support both single and multiple save locations
        save_file_locations = normalize_save_file_locations(data)

        banner = (data.get('banner') or '').strip()

        if not name or not save_file_locations:
            return json_response_error('Game name and at least one save file location are required.', status=400)

        if not save_file_locations:
            return json_response_error('At least one valid save file location is required.', status=400)

        duplicate_error = validate_unique_save_file_locations(save_file_locations)
        if duplicate_error:
            return duplicate_error

        # Ensure unique name (excluding this game)
        if Game.objects.exclude(pk=game.id).filter(name=name).exists():
            return json_response_error('A game with this name already exists.', status=400)

        game.name = name
        game.save_file_locations = save_file_locations

        # Clean up old mappings and generate new ones
        game.cleanup_path_mappings()  # Remove mappings for deleted paths
        game.generate_path_mappings()  # Generate mappings for current paths

        # Handle banner update
        if banner:
            game.banner_url = banner  # Store original URL immediately

            # Skip download if banner URL is from same server (localhost/local IP)
            from SaveNLoad.utils.image_utils import is_local_url
            if is_local_url(banner, request):
                # Local URL - skip download, just store the URL
                print(f"Banner URL is local ({banner}) - skipping download")
            else:
                # Download and cache banner (increased timeout for external URLs)
                try:
                    success, message, file_obj = download_image_from_url(banner, timeout=10)
                    if success and file_obj:
                        try:
                            # Delete old banner if exists
                            if game.banner:
                                try:
                                    old_path = game.banner.path
                                    if os.path.exists(old_path):
                                        os.remove(old_path)
                                except Exception as e:
                                    print(f"WARNING: Failed to delete old banner: {e}")

                            # Determine file extension
                            parsed = urlparse(banner)
                            ext = os.path.splitext(parsed.path)[1] or '.jpg'
                            game.banner.save(f"banner_{game.id}{ext}", File(file_obj), save=False)
                            # Refresh game object to ensure banner field is updated
                            game.refresh_from_db()
                            # Update banner_url to local URL after successful download
                            if game.banner:
                                local_url = request.build_absolute_uri(game.banner.url) if request else game.banner.url
                                game.banner_url = local_url
                                game.save(update_fields=['banner_url'])
                            # Clean up temp file
                            if hasattr(file_obj, 'name'):
                                os.unlink(file_obj.name)
                            print(
                                f"Successfully downloaded and cached banner for game {game.id}: {game.banner.name if game.banner else 'NOT SET'}")
                        except Exception as e:
                            print(f"ERROR: Failed to save cached banner for game {game.id}: {e}")
                            # Continue - banner_url is already stored as fallback
                    else:
                        print(f"WARNING: Failed to download banner for game {game.id}: {message}")
                        # Continue - banner_url is already stored as fallback
                except Exception as e:
                    print(f"ERROR: Banner download failed for game {game.id}: {e}")
                    # Don't block the save operation - banner will load from URL
        else:
            # If banner is cleared, also clear cached file
            if game.banner:
                try:
                    old_path = game.banner.path
                    if os.path.exists(old_path):
                        os.remove(old_path)
                except Exception as e:
                    print(f"WARNING: Failed to delete banner: {e}")
            game.banner = None
            game.banner_url = None

        game.save()

        return json_response_success(
            data={
                'game': {
                    'id': game.id,
                    'name': game.name,
                    'banner': get_image_url_or_fallback(game, request),  # Display URL for preview
                    'banner_url': game.banner_url or '',  # Original URL for input field
                    'save_file_locations': game.save_file_locations,
                }
            }
        )
    except Exception as e:
        import traceback
        print(f"ERROR in game_detail: {e}")
        print(traceback.format_exc())
        return json_response_error(f'Failed to process game: {str(e)}', status=500)


@login_required
@require_http_methods(["POST"])
def delete_game(request, game_id):
    """
    Dedicated delete endpoint (alias for DELETE for clients that prefer POST).

    Args:
        request: Django request object.
        game_id: Game identifier.

    Returns:
        JsonResponse with deletion status or error.
    """
    user = get_current_user(request)
    error_response = check_admin_or_error(user)
    if error_response:
        return error_response

    # Get game or return error
    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response

    return _handle_game_deletion(request, game, user)


@login_required
@require_http_methods(["POST"])
def update_account_settings(request):
    """
    Update account settings (email and/or password).

    Args:
        request: Django request object.

    Returns:
        JsonResponse with update status or error.
    """
    user = get_current_user(request)
    if not user:
        return json_response_error('Unauthorized', status=403)

    data, error_response = parse_json_body(request)
    if error_response:
        return error_response

    # Sanitize inputs using input_sanitizer utilities
    from SaveNLoad.views.input_sanitizer import sanitize_email, validate_password_strength

    # Sanitize email
    raw_email = data.get('email', '').strip()
    email = sanitize_email(raw_email) if raw_email else None

    # If email was provided but sanitization failed, it's invalid
    if raw_email and not email:
        return json_response_error('Invalid email format.', status=400)

    # Get password inputs (strip whitespace)
    current_password = data.get('current_password', '').strip()
    new_password = data.get('new_password', '').strip()
    confirm_password = data.get('confirm_password', '').strip()

    # Validate password inputs using sanitizer (checks length and dangerous characters)
    if current_password:
        is_valid, error_msg = validate_password_strength(current_password)
        if not is_valid:
            return json_response_error(f'Current password: {error_msg}', status=400)
        if '\x00' in current_password:
            return json_response_error('Invalid characters in current password.', status=400)

    if new_password:
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            return json_response_error(f'New password: {error_msg}', status=400)
        if '\x00' in new_password:
            return json_response_error('Invalid characters in new password.', status=400)

    if confirm_password:
        is_valid, error_msg = validate_password_strength(confirm_password)
        if not is_valid:
            return json_response_error(f'Confirm password: {error_msg}', status=400)
        if '\x00' in confirm_password:
            return json_response_error('Invalid characters in confirm password.', status=400)

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

        # Password strength already validated above

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
    """
    Get statistics about the operation queue (Admin only).

    Args:
        request: Django request object.

    Returns:
        JsonResponse with queue statistics.
    """
    user = get_current_user(request)
    error_response = check_admin_or_error(user)
    if error_response:
        return error_response

    from SaveNLoad.utils.redis_client import get_redis_client
    from SaveNLoad.services.redis_operation_service import OperationStatus
    from SaveNLoad.models.operation_constants import OperationType
    from django.utils import timezone
    from datetime import timedelta

    redis_client = get_redis_client()

    # Get all operation keys
    operation_keys = redis_client.keys('operation:*')

    # Get all operations
    all_operations = []
    for key in operation_keys:
        operation_hash = redis_client.hgetall(key)
        if operation_hash:
            all_operations.append({
                'status': operation_hash.get('status', ''),
                'type': operation_hash.get('type', ''),
                'created_at': operation_hash.get('created_at', ''),
                'started_at': operation_hash.get('started_at', '')
            })

    total_count = len(all_operations)

    # Count by status
    status_counts = {
        OperationStatus.PENDING: 0,
        OperationStatus.IN_PROGRESS: 0,
        OperationStatus.COMPLETED: 0,
        OperationStatus.FAILED: 0,
    }
    for op in all_operations:
        status = op.get('status', '')
        if status in status_counts:
            status_counts[status] += 1

    # Count by type
    type_counts = {
        OperationType.SAVE: 0,
        OperationType.LOAD: 0,
        OperationType.LIST: 0,
        OperationType.DELETE: 0,
        OperationType.BACKUP: 0,
        OperationType.OPEN_FOLDER: 0,
    }
    for op in all_operations:
        op_type = op.get('type', '')
        if op_type in type_counts:
            type_counts[op_type] += 1

    # Get oldest and newest operations
    oldest = None
    newest = None
    if all_operations:
        sorted_ops = sorted(all_operations, key=lambda x: x.get('created_at', ''))
        oldest = sorted_ops[0] if sorted_ops else None
        newest = sorted_ops[-1] if sorted_ops else None

    # Count operations older than 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    old_count = 0
    for op in all_operations:
        created_at_str = op.get('created_at')
        if created_at_str:
            try:
                from datetime import datetime
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                if timezone.is_aware(created_at):
                    created_at = timezone.make_naive(created_at)
                if created_at < timezone.make_naive(thirty_days_ago):
                    old_count += 1
            except:
                pass

    # Count operations older than 7 days
    seven_days_ago = timezone.now() - timedelta(days=7)
    week_old_count = 0
    for op in all_operations:
        created_at_str = op.get('created_at')
        if created_at_str:
            try:
                from datetime import datetime
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                if timezone.is_aware(created_at):
                    created_at = timezone.make_naive(created_at)
                if created_at < timezone.make_naive(seven_days_ago):
                    week_old_count += 1
            except:
                pass

    # Count stuck operations (in progress for more than 1 hour)
    one_hour_ago = timezone.now() - timedelta(hours=1)
    stuck_count = 0
    for op in all_operations:
        if op.get('status') == OperationStatus.IN_PROGRESS:
            started_at_str = op.get('started_at')
            if started_at_str:
                try:
                    from datetime import datetime
                    started_at = datetime.fromisoformat(started_at_str.replace('Z', '+00:00'))
                    if timezone.is_aware(started_at):
                        started_at = timezone.make_naive(started_at)
                    if started_at < timezone.make_naive(one_hour_ago):
                        stuck_count += 1
                except:
                    pass

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
        'oldest_operation': oldest.get('created_at') if oldest else None,
        'newest_operation': newest.get('created_at') if newest else None,
        'old_count_30_days': old_count,
        'old_count_7_days': week_old_count,
        'stuck_count': stuck_count,
    }

    return json_response_success(data=stats)


@login_required
@require_http_methods(["POST"])
def operation_queue_cleanup(request):
    """
    Cleanup operation queue (Admin only).

    Args:
        request: Django request object.

    Returns:
        JsonResponse with cleanup results.
    """
    user = get_current_user(request)
    error_response = check_admin_or_error(user)
    if error_response:
        return error_response

    from SaveNLoad.utils.redis_client import get_redis_client
    from SaveNLoad.services.redis_operation_service import OperationStatus

    data, error_response = parse_json_body(request)
    if error_response:
        return error_response

    cleanup_type = data.get('type', '').strip()

    if cleanup_type == 'completed':
        return cleanup_operations_by_status(
            status=OperationStatus.COMPLETED,
            no_items_message='No completed operations to delete',
            success_message_template='Deleted {count} completed operation(s)'
        )

    elif cleanup_type == 'failed':
        return cleanup_operations_by_status(
            status=OperationStatus.FAILED,
            no_items_message='No failed operations to delete',
            success_message_template='Deleted {count} failed operation(s)'
        )

    elif cleanup_type == 'old':
        return cleanup_operations_by_age(
            days=30,
            no_items_message='No old operations (30+ days) to delete',
            success_message_template='Deleted {count} old operation(s) (30+ days)'
        )

    elif cleanup_type == 'all':
        # Delete all operations
        redis_client = get_redis_client()
        operation_keys = redis_client.keys('operation:*')
        deleted_count = len(operation_keys)

        for key in operation_keys:
            redis_client.delete(key)

        if deleted_count == 0:
            return json_response_success(
                message='No operations to delete - queue is empty',
                data={'deleted_count': 0}
            )

        return json_response_success(
            message=f'Deleted all {deleted_count} operation(s)',
            data={'deleted_count': deleted_count}
        )

    else:
        return json_response_error('Invalid cleanup type. Must be: completed, failed, old, or all', status=400)


@login_required
@require_http_methods(["GET"])
def list_users(request):
    """
    List all users with pagination (Admin only).

    Args:
        request: Django request object.

    Returns:
        JsonResponse with paginated user list.
    """
    user = get_current_user(request)
    error_response = check_admin_or_error(user)
    if error_response:
        return error_response

    try:
        from SaveNLoad.models import SimpleUsers

        # Get pagination parameters
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 25))  # Default 25 per page

        # Ensure valid page and page_size
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 25
        if page_size > 100:  # Max 100 per page to prevent abuse
            page_size = 100

        # Get search query if provided
        search_query = request.GET.get('q', '').strip()

        # Get all users (or filtered by search) - exclude current user
        users_query = SimpleUsers.objects.all().exclude(id=user.id).order_by('username')

        # Filter by search query if provided
        if search_query:
            users_query = users_query.filter(
                models.Q(username__icontains=search_query) |
                models.Q(email__icontains=search_query)
            )

        # Calculate pagination
        total_count = users_query.count()
        total_pages = (total_count + page_size - 1) // page_size  # Ceiling division

        # Ensure page doesn't exceed total pages
        if page > total_pages and total_pages > 0:
            page = total_pages

        # Apply pagination
        offset = (page - 1) * page_size
        users = users_query[offset:offset + page_size]

        # Build user list
        users_list = []
        for u in users:
            users_list.append({
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'role': u.role,
            })

        return json_response_success(
            data={
                'users': users_list,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_previous': page > 1,
                }
            }
        )
    except Exception as e:
        print(f"ERROR: Error listing users: {str(e)}")
        return json_response_error(f'Failed to list users: {str(e)}', status=500)


def _queue_user_deletion_operations(user: 'SimpleUsers', admin_user, request=None):
    """
    Queue operations to delete all FTP saves for a user before deletion.
    Creates a single delete operation for the entire user directory.
    The operation is assigned to the admin's worker (the one making the delete request).
    
    Args:
        user: SimpleUsers instance to delete
        admin_user: Admin user making the delete request (their worker will handle the deletion)
        request: Optional request object for worker lookup
    
    Returns:
        tuple: (success: bool, error_message: str or None, operation_id: int or None)
        - (True, None, operation_id) if operations were queued successfully
        - (True, "no_saves", None) if no saves exist (immediate deletion safe)
        - (False, error_message, None) if FTP cleanup failed (no worker available, etc.)
    """
    from SaveNLoad.models.save_folder import SaveFolder
    from SaveNLoad.models.operation_constants import OperationType
    from SaveNLoad.services.redis_operation_service import create_operation

    try:
        # Get all save folders for this user
        save_folders = SaveFolder.objects.filter(user=user)

        if not save_folders.exists():
            print(f"No save folders found for user {user.id} ({user.username}), no FTP cleanup needed")
            # No saves to clean up, so we can return a special flag indicating immediate deletion is safe
            return (True, "no_saves", None)  # Special flag: no saves means immediate deletion is safe

        # Get the admin's worker (from session - automatic association)
        from SaveNLoad.views.api_helpers import get_client_worker_or_error
        client_worker, error_response = get_client_worker_or_error(admin_user, request)
        if error_response:
            error_msg = f"No active client worker available. Cannot delete FTP saves for user '{user.username}'. Please ensure a client worker is running and try again."
            print(
                f"WARNING: No active client worker available for admin {admin_user.username}, cannot delete FTP saves for user {user.id}")
            return (False, error_msg, None)

        # Create DELETE operation for the entire user directory (username/)
        # This will delete all saves for the user across all games
        # Operation is assigned to the admin's worker
        operation_id = create_operation(
            {
                'operation_type': OperationType.DELETE,
                'user_id': user.id,  # User being deleted (for tracking)
                'game_id': None,  # No game association for user deletion
                'local_save_path': '',
                'save_folder_number': None,  # Deleting entire user directory
                'smb_path': user.username,  # Full path to user directory (just username/)
                'path_index': None
            },
            client_worker  # Admin's worker handles the deletion
        )

        print(
            f"Queued delete operation for user directory: {user.username}/ (assigned to admin's worker: {client_worker})")
        return (True, None, operation_id)  # Return operation_id for progress tracking
    except Exception as e:
        error_msg = f"Error queueing user deletion operations: {str(e)}"
        print(f"ERROR: Error queueing user deletion operations for user {user.id}: {e}")
        return (False, error_msg, None)


def _handle_user_deletion(request, user, admin_user):
    """
    Helper to handle user deletion logic
    Returns: JsonResponse

    Args:
        request: Django request object.
        user: User instance to delete.
        admin_user: Admin requesting deletion.

    Returns:
        JsonResponse indicating queued or completed deletion.
    """
    # Queue operations to delete all FTP saves for this user
    # Use admin's worker (the one making the delete request)
    # Do NOT delete user if FTP cleanup fails to queue
    success, error_message, operation_id = _queue_user_deletion_operations(user, admin_user=admin_user, request=request)
    if not success:
        return json_response_error(error_message or "Failed to queue FTP cleanup operations", status=503)

    # If no saves exist, delete immediately (nothing to clean up)
    if error_message == "no_saves":
        user.delete()
        print(f"User {user.id} ({user.username}) deleted immediately - no FTP saves to clean up")
        return json_response_success(message=f'User "{user.username}" deleted successfully')
    else:
        # Mark user for deletion - actual deletion happens after FTP operation completes successfully
        user.pending_deletion = True
        user.save()
        print(
            f"User {user.id} ({user.username}) marked for deletion - will be deleted after FTP cleanup operation completes")
        return json_response_success(
            message=f'User "{user.username}" deletion queued. FTP cleanup in progress...',
            data={'operation_id': operation_id}
        )


@login_required
@require_http_methods(["POST", "DELETE"])
def delete_user(request, user_id):
    """
    Delete a user account (Admin only).

    Args:
        request: Django request object.
        user_id: User identifier.

    Returns:
        JsonResponse with deletion status or error.
    """
    admin_user = get_current_user(request)
    error_response = check_admin_or_error(admin_user)
    if error_response:
        return error_response

    try:
        from SaveNLoad.models import SimpleUsers

        # Get target user
        try:
            target_user = SimpleUsers.objects.get(id=user_id)
        except SimpleUsers.DoesNotExist:
            return json_response_error('User not found.', status=404)

        # Prevent admin from deleting themselves
        if target_user.id == admin_user.id:
            return json_response_error('You cannot delete your own account.', status=400)

        return _handle_user_deletion(request, target_user, admin_user)
    except Exception as e:
        print(f"ERROR: Error deleting user: {str(e)}")
        return json_response_error(f'Failed to delete user: {str(e)}', status=500)


@login_required
@require_http_methods(["POST"])
def reset_user_password(request, user_id):
    """
    Reset a user's password to default constant (Admin only).

    Args:
        request: Django request object.
        user_id: User identifier.

    Returns:
        JsonResponse with reset status or error.
    """
    user = get_current_user(request)
    error_response = check_admin_or_error(user)
    if error_response:
        return error_response

    try:
        from SaveNLoad.models import SimpleUsers
        from SaveNLoad.views.input_sanitizer import validate_password_strength
        import os
        from django.conf import settings

        # Get target user
        try:
            target_user = SimpleUsers.objects.get(id=user_id)
        except SimpleUsers.DoesNotExist:
            return json_response_error('User not found.', status=404)

        # Prevent admin from resetting their own password
        if target_user.id == user.id:
            return json_response_error('You cannot reset your own password through this feature.', status=400)

        # Get default password from environment variable
        DEFAULT_PASSWORD = os.getenv('RESET_PASSWORD_DEFAULT')

        # Validate default password strength (reuse existing validation)
        is_valid, error_msg = validate_password_strength(DEFAULT_PASSWORD)
        if not is_valid:
            return json_response_error(f'Default password validation failed: {error_msg}', status=500)

        # Reset password using existing set_password method
        target_user.set_password(DEFAULT_PASSWORD)
        target_user.save()

        return json_response_success(
            message=f'Password reset successfully for user "{target_user.username}". Default password has been set.',
            data={
                'user': {
                    'id': target_user.id,
                    'username': target_user.username,
                    'email': target_user.email,
                },
                'password': DEFAULT_PASSWORD  # Include password in response
            }
        )
    except Exception as e:
        print(f"ERROR: Error resetting user password: {str(e)}")
        return json_response_error(f'Failed to reset password: {str(e)}', status=500)
"""
DEPRECATED: Legacy Django function views retained for reference only.
Do not use in production; replaced by DRF API views.
"""
