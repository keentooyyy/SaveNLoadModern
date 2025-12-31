"""
Common helper functions for API endpoints
"""
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from SaveNLoad.models import Game
from SaveNLoad.services.redis_worker_service import (
    get_user_workers,
    is_worker_online
)
from SaveNLoad.views.custom_decorators import get_current_user
from SaveNLoad.utils.image_utils import get_image_url_or_fallback
from django.utils import timezone
from datetime import timedelta
import json
import os


def delete_game_banner_file(game):
    """
    Delete the banner file associated with a game
    Returns: True if deleted successfully or no banner exists, False on error
    """
    if not game or not game.banner:
        return True
    
    try:
        if game.banner.name:
            banner_path = game.banner.path
            if os.path.exists(banner_path):
                os.remove(banner_path)
                print(f"Deleted banner file for game {game.id} ({game.name}): {banner_path}")
            return True
    except Exception as e:
        print(f"WARNING: Failed to delete banner file for game {game.id} ({game.name}): {e}")
        return False
    
    return True


def json_response_error(message: str, status: int = 400) -> JsonResponse:
    """Helper to create error JSON responses"""
    return JsonResponse({'error': message}, status=status)


def json_response_success(message: str = None, data: dict = None) -> JsonResponse:
    """Helper to create success JSON responses"""
    response = {'success': True}
    if message:
        response['message'] = message
    if data:
        response.update(data)
    return JsonResponse(response)


def parse_json_body(request):
    """
    Parse JSON body from request
    Returns: (data_dict, error_response_or_none)
    """
    try:
        data = json.loads(request.body or "{}")
        return data, None
    except json.JSONDecodeError:
        return {}, json_response_error('Invalid JSON body', status=400)


def normalize_save_file_locations(data, single_key='save_file_location', multi_key='save_file_locations'):
    """
    Normalize save file locations from a payload into a list of cleaned paths.
    Returns: list of non-empty path strings
    """
    save_file_locations = data.get(multi_key, [])
    
    if not save_file_locations:
        single_location = (data.get(single_key) or '').strip()
        if single_location:
            save_file_locations = [single_location]
    
    # Handle single string payloads
    if isinstance(save_file_locations, str):
        save_file_locations = [save_file_locations]
    
    return [loc.strip() for loc in save_file_locations if loc and loc.strip()]


def get_game_or_error(game_id):
    """
    Get game by ID or return error response
    Returns: (game_object, error_response_or_none)
    """
    try:
        game = Game.objects.get(pk=game_id)
        return game, None
    except Game.DoesNotExist:
        return None, json_response_error('Game not found', status=404)


def get_client_worker_or_error(user, request=None):
    """
    Get client worker for a user or return error response
    Uses Redis to check if user owns an active worker
    Returns: (client_id_string, error_response_or_none)
    """
    if not user:
        return None, json_response_error('User is required', status=400)
    
    # Get online workers for this user
    worker_ids = get_user_workers(user.id)
    
    if not worker_ids:
        return None, JsonResponse({
            'error': 'No client worker paired. Please claim a worker in settings.',
            'requires_worker': True
        }, status=503)
    
    # Return first worker (most recent)
    client_id = worker_ids[0]
    
    if not is_worker_online(client_id):
        return None, JsonResponse({
            'error': f'Client worker ({client_id}) is offline. Please ensure it is running.',
            'requires_worker': True
        }, status=503)
        
    return client_id, None


def check_admin_or_error(user):
    """
    Check if user is admin, return error response if not
    Returns: error_response_or_none
    """
    if not user or not user.is_admin():
        return json_response_error('Unauthorized', status=403)
    return None


def redirect_if_logged_in(request):
    """
    Redirect user to appropriate dashboard if already logged in
    Returns: redirect_response_or_none
    """
    user = get_current_user(request)
    if user:
        if user.is_admin():
            return redirect(reverse('admin:dashboard'))
        else:
            return redirect(reverse('user:dashboard'))
    return None


def json_response_with_redirect(message, redirect_url):
    """
    Create JSON response with redirect header for AJAX requests
    """
    response = json_response_success(message=message)
    response['X-Redirect-URL'] = redirect_url
    return response


def json_response_field_errors(field_errors, general_errors=None, message=None):
    """
    Create JSON response with field errors (for form validation)
    """
    response = {
        'success': False,
        'field_errors': field_errors
    }
    if general_errors:
        response['errors'] = general_errors
    if message:
        response['message'] = message
    return JsonResponse(response, status=400)


def get_client_worker_by_id_or_error(client_id):
    """
    Get client worker by client_id or return error response
    Returns: (client_id_string, error_response_or_none)
    """
    if not client_id:
        return None, json_response_error('client_id is required', status=400)
    
    if not is_worker_online(client_id):
        return None, json_response_error('Client not registered or offline', status=404)
    
    return client_id, None


def get_save_folder_or_error(user, game, folder_number):
    """
    Get save folder by number or return error response
    Returns: (save_folder_object, error_response_or_none)
    """
    from SaveNLoad.models.save_folder import SaveFolder
    
    if not user:
        return None, json_response_error('User is required', status=400)
    
    if not game:
        return None, json_response_error('Game is required', status=400)
    
    if folder_number is None:
        return None, json_response_error('Save folder number is required', status=400)
    
    save_folder = SaveFolder.get_by_number(user, game, folder_number)
    if not save_folder:
        return None, json_response_error('Save folder not found', status=404)
    
    # Validate save folder has required fields
    if not save_folder.folder_number:
        return None, json_response_error('Save folder number is missing', status=500)
    
    if not save_folder.smb_path:
        return None, json_response_error('Save folder path is missing', status=500)
    
    return save_folder, None


def validate_save_folder_or_error(save_folder):
    """
    Validate save folder has required fields or return error response
    Returns: (save_folder_object, error_response_or_none)
    """
    if not save_folder:
        return None, json_response_error('Save folder not found', status=404)
    
    if not save_folder.folder_number:
        return None, json_response_error('Save folder number is missing', status=500)
    
    if not save_folder.smb_path:
        return None, json_response_error('Save folder path is missing', status=500)
    
    return save_folder, None


def get_local_save_path_or_error(data, game, field_name='local_save_path'):
    """
    Get local save path from data or game default, validate it exists
    Returns: (local_save_path_string, error_response_or_none)
    Note: For games with multiple paths, this returns the first path
    """
    local_save_path = data.get(field_name, '').strip()
    
    # If not provided, use game's default (first path if multiple)
    if not local_save_path:
        if game and game.save_file_locations:
            # Get first path from array
            local_save_path = game.save_file_locations[0] if isinstance(game.save_file_locations, list) and len(game.save_file_locations) > 0 else ''
    
    # Validate it's not empty
    if not local_save_path or not local_save_path.strip():
        return None, json_response_error('Local save path is required', status=400)
    
    return local_save_path, None


def get_all_save_paths_or_error(data, game, field_name='local_save_paths'):
    """
    Get all save paths from data or game default, split by newlines if needed
    Returns: (list_of_paths, error_response_or_none)
    """
    # First check if paths are provided in the request as a list
    save_paths = data.get(field_name, [])
    
    # If not provided as list, check if it's a string (single path)
    if not save_paths:
        single_path = data.get('local_save_path', '').strip()
        if single_path:
            save_paths = [single_path]
    
    # If still no paths, use game's default save_file_locations
    if not save_paths:
        if game and game.save_file_locations:
            # Use the JSON array directly
            if isinstance(game.save_file_locations, list):
                save_paths = [path.strip() for path in game.save_file_locations if path and path.strip()]
            else:
                # Fallback: if it's somehow still a string, treat as single path
                save_paths = [str(game.save_file_locations).strip()] if game.save_file_locations else []
    
    # Filter out empty paths
    save_paths = [path.strip() for path in save_paths if path and path.strip()]
    
    # Validate at least one path exists
    if not save_paths:
        return None, json_response_error('At least one save file location is required', status=400)
    
    return save_paths, None


def resolve_save_paths_or_error(data, game, require_non_empty_if_provided=False):
    """
    Resolve save paths and determine if multi-path handling should be used.
    Returns: (save_paths_list_or_none, error_response_or_none, use_multi_paths_bool)
    """
    if 'local_save_paths' in data:
        save_paths = data.get('local_save_paths', [])
        if require_non_empty_if_provided and isinstance(save_paths, list) and len(save_paths) == 0:
            return None, json_response_error(
                'local_save_paths cannot be empty. Please provide at least one save file path.',
                status=400
            ), True
        
        save_paths, error_response = get_all_save_paths_or_error(data, game, 'local_save_paths')
        if error_response:
            return None, error_response, True
        
        return save_paths, None, True
    
    if game.save_file_locations and isinstance(game.save_file_locations, list) and len(game.save_file_locations) > 1:
        save_paths = [path.strip() for path in game.save_file_locations if path and path.strip()]
        if not save_paths:
            return None, json_response_error('Game has invalid save file locations', status=400), True
        return save_paths, None, True
    
    return None, None, False


def get_game_paths_or_error(game):
    """
    Validate and return normalized save paths configured for a game.
    Returns: (set_of_normalized_paths, error_response_or_none)
    """
    if not game.save_file_locations:
        return None, json_response_error('Game has no save file locations configured', status=400)
    if not isinstance(game.save_file_locations, list):
        return None, json_response_error('Game save file locations is invalid', status=400)
    
    game_paths = {os.path.normpath(p) for p in game.save_file_locations if p}
    if not game_paths:
        return None, json_response_error('Game has invalid save file locations', status=400)
    
    return game_paths, None


def validate_game_path_mapping_or_error(game, path, use_subfolders):
    """
    Validate a path belongs to a game's configured paths and return its path_index if needed.
    Returns: (path_index_or_none, error_response_or_none)
    """
    game_paths, error_response = get_game_paths_or_error(game)
    if error_response:
        return None, error_response
    
    normalized_path = os.path.normpath(path)
    if normalized_path not in game_paths:
        return None, json_response_error(
            f'Path "{path}" is not configured for this game. Please edit the game to add this path.',
            status=400
        )
    
    if use_subfolders:
        path_index = game.get_path_index(path)
        if path_index is None:
            return None, json_response_error(
                f'Path "{path}" is not mapped. Please edit the game to configure path mappings.',
                status=400
            )
        return path_index, None
    
    return None, None


def get_latest_save_folder_or_error(user, game):
    """
    Get latest save folder for user+game or return error response
    Returns: (save_folder_object, error_response_or_none)
    """
    from SaveNLoad.models.save_folder import SaveFolder
    
    if not user:
        return None, json_response_error('User is required', status=400)
    
    if not game:
        return None, json_response_error('Game is required', status=400)
    
    save_folder = SaveFolder.get_latest(user, game)
    if not save_folder:
        return None, json_response_error('No save files found', status=404)
    
    # Validate save folder has required fields
    if not save_folder.folder_number:
        return None, json_response_error('Save folder number is missing', status=500)
    
    if not save_folder.smb_path:
        return None, json_response_error('Save folder path is missing', status=500)
    
    return save_folder, None


def create_operation_response(operation_id, client_id, message=None, extra_data=None):
    """
    Create standardized operation response with operation_id and client_id
    Returns: JsonResponse with operation data
    
    Args:
        operation_id: Operation ID string
        client_id: Client ID string
        message: Optional success message
        extra_data: Optional dict of additional data to include
    """
    data = {
        'operation_id': operation_id,
        'client_id': client_id
    }
    
    # Merge any extra data
    if extra_data:
        data.update(extra_data)
    
    return json_response_success(message=message, data=data)


def get_operation_or_error(operation_id, user=None):
    """
    Get operation by ID or return error response
    Optionally verify operation belongs to user
    
    Returns: (operation_dict, error_response_or_none)
    """
    from SaveNLoad.services.redis_operation_service import get_operation
    
    operation = get_operation(operation_id)
    
    if not operation:
        return None, json_response_error('Operation not found', status=404)
    
    # If user provided, verify operation belongs to user
    if user and operation.get('user_id') != user.id:
        return None, json_response_error('Operation not found', status=404)
    
    return operation, None


def get_user_game_last_played(user, limit=None):
    """
    Get last_played timestamps for all games for a user from SaveFolder records
    Returns: dict mapping game_id -> last_played datetime
    
    Args:
        user: User instance
        limit: Optional limit for recent games (e.g., 10 for top 10)
    """
    from SaveNLoad.models.save_folder import SaveFolder
    from django.db.models import Max
    
    query = SaveFolder.objects.filter(user=user).values('game').annotate(
        last_played=Max('created_at')
    )
    
    if limit:
        query = query.order_by('-last_played')[:limit]
    
    return {sf['game']: sf['last_played'] for sf in query}


def get_game_save_locations(game):
    """
    Return a normalized list of save file locations for a game.
    """
    if not game or not isinstance(game.save_file_locations, list):
        return []
    return [path for path in game.save_file_locations if path is not None]


def build_game_data_dict(game, last_played=None, include_id=False, include_footer=False, footer_formatter=None):
    """
    Build standardized game data dictionary
    Returns: dict with game data
    
    Args:
        game: Game instance
        last_played: Optional datetime for last_played
        include_id: Whether to include game.id
        include_footer: Whether to include footer field (uses last_played)
        footer_formatter: Optional function to format footer (e.g., format_last_played)
    """
    data = {
        'title': game.name,
        'image': get_image_url_or_fallback(game, request),
    }
    
    if include_id:
        data['id'] = game.id
    
    if include_footer and last_played:
        if footer_formatter:
            data['footer'] = footer_formatter(last_played)
        else:
            data['footer'] = last_played.isoformat() if last_played else None
    
    if last_played and not include_footer:
        data['playtime'] = footer_formatter(last_played) if footer_formatter else (last_played.isoformat() if last_played else None)
    
    return data


def safe_delete_operations(queryset, expected_model='SaveNLoad.OperationQueue'):
    """
    Safely delete operations and verify only expected model was deleted
    Returns: (deleted_count, is_safe)
    
    Args:
        queryset: QuerySet to delete
        expected_model: Expected model name in deleted_objects dict
    """
    deleted_count, deleted_objects = queryset.delete()
    
    # Verify only expected model was deleted (safety check)
    is_safe = True
    if deleted_objects:
        if expected_model not in deleted_objects or len(deleted_objects) > 1:
            is_safe = False
            print(f"WARNING: Unexpected objects deleted: {deleted_objects}")
    
    return deleted_count, is_safe


def cleanup_operations_by_status(status, no_items_message, success_message_template):
    """
    Cleanup operations by status with standardized pattern
    Returns: JsonResponse
    
    Args:
        status: OperationStatus constant
        no_items_message: Message when no items to delete
        success_message_template: Template for success message (e.g., "Deleted {count} completed operation(s)")
    """
    from SaveNLoad.utils.redis_client import get_redis_client
    from SaveNLoad.services.redis_operation_service import OperationStatus
    
    redis_client = get_redis_client()
    
    # Get all operations with the specified status
    operation_keys = redis_client.keys('operation:*')
    matching_keys = []
    for key in operation_keys:
        op_status = redis_client.hget(key, 'status')
        if op_status == status:
            matching_keys.append(key)
    
    count = len(matching_keys)
    if count == 0:
        return json_response_success(
            message=no_items_message,
            data={'deleted_count': 0}
        )
    
    # Delete operations
    deleted_count = 0
    for key in matching_keys:
        redis_client.delete(key)
        deleted_count += 1
    
    return json_response_success(
        message=success_message_template.format(count=deleted_count),
        data={'deleted_count': deleted_count}
    )


def cleanup_operations_by_age(days, no_items_message, success_message_template):
    """
    Cleanup operations older than specified days
    Returns: JsonResponse
    
    Args:
        days: Number of days (e.g., 30 for 30+ days old)
        no_items_message: Message when no items to delete
        success_message_template: Template for success message
    """
    from SaveNLoad.utils.redis_client import get_redis_client
    from datetime import timedelta
    
    threshold = timezone.now() - timedelta(days=days)
    redis_client = get_redis_client()
    
    # Get all operations older than threshold
    operation_keys = redis_client.keys('operation:*')
    old_keys = []
    for key in operation_keys:
        created_at_str = redis_client.hget(key, 'created_at')
        if created_at_str:
            try:
                from datetime import datetime
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                if timezone.is_aware(created_at):
                    created_at = timezone.make_naive(created_at)
                if created_at < timezone.make_naive(threshold):
                    old_keys.append(key)
            except:
                pass
    
    old_count = len(old_keys)
    if old_count == 0:
        return json_response_success(
            message=no_items_message,
            data={'deleted_count': 0}
        )
    
    # Delete old operations
    deleted_count = 0
    for key in old_keys:
        redis_client.delete(key)
        deleted_count += 1
    
    return json_response_success(
        message=success_message_template.format(count=deleted_count),
        data={'deleted_count': deleted_count}
    )
