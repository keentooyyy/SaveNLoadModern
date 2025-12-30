"""
API endpoints for save/load operations
These endpoints are used by the client worker to perform save/load operations
"""
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from SaveNLoad.views.custom_decorators import login_required, get_current_user
from SaveNLoad.views.api_helpers import (
    parse_json_body,
    get_game_or_error,
    get_client_worker_or_error,
    get_local_save_path_or_error,
    get_all_save_paths_or_error,
    get_save_folder_or_error,
    get_latest_save_folder_or_error,
    validate_save_folder_or_error,
    create_operation_response,
    get_operation_or_error,
    json_response_error,
    json_response_success
)
from SaveNLoad.utils.string_utils import transform_path_error_message
from SaveNLoad.utils.datetime_utils import calculate_progress_percentage, to_isoformat
from SaveNLoad.utils.model_utils import filter_by_user_and_game
from SaveNLoad.models.save_folder import SaveFolder
from SaveNLoad.models import Game
from SaveNLoad.services.redis_operation_service import create_operation
import json
import os
import zipfile
import tempfile
import io
from pathlib import Path
from django.conf import settings


def _build_full_remote_path(username: str, game_name: str, save_folder_number: int, 
                           path_index: int = None) -> str:
    """
    Build complete remote FTP path for the client worker.
    This is the ONLY place path construction should happen.
    
    Args:
        username: User's username
        game_name: Game name (will be sanitized)
        save_folder_number: Save folder number
        path_index: Optional path index for multi-path games (1, 2, 3, etc.)
    
    Returns:
        Complete remote path like "username/GameName/save_1" or "username/GameName/save_1/path_2"
    """
    # Sanitize game name - keep only alphanumeric, spaces, hyphens, and underscores
    safe_game_name = "".join(c for c in game_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_game_name = safe_game_name.replace(' ', '_')
    
    # Build base path
    remote_path = f"{username}/{safe_game_name}/save_{save_folder_number}"
    
    # Add path_index if provided (for multi-path games)
    if path_index is not None:
        remote_path = f"{remote_path}/path_{path_index}"
    
    return remote_path


@login_required
@require_http_methods(["POST"])
def save_game(request, game_id):
    """
    Save game endpoint - queues operation for client worker
    Expects: {'local_save_path': 'path/to/save/files', 'local_save_paths': ['path1', 'path2'] (optional), 'client_id': 'optional'}
    
    If local_save_paths is provided, it will save all locations to separate subfolders (path_1, path_2, etc.)
    """
    from SaveNLoad.models.operation_constants import OperationType
    
    try:
        user = get_current_user(request)
        
        # Get game or return error
        game, error_response = get_game_or_error(game_id)
        if error_response:
            return error_response
        
        # Parse JSON body
        data, error_response = parse_json_body(request)
        if error_response:
            return error_response
        
        # Get client worker for this user
        client_worker, error_response = get_client_worker_or_error(user, request)
        if error_response:
            return error_response
    
        # Check if multiple paths are provided OR if game has multiple paths
        # First check if explicit paths are provided in request
        if 'local_save_paths' in data:
            # Handle multiple save locations from request
            save_paths = data.get('local_save_paths', [])
            
            # If empty array provided, fail immediately - no fallback
            if isinstance(save_paths, list) and len(save_paths) == 0:
                return json_response_error('local_save_paths cannot be empty. Please provide at least one save file path.', status=400)
            
            # Validate provided paths
            save_paths, error_response = get_all_save_paths_or_error(data, game, 'local_save_paths')
            if error_response:
                return error_response
        # Check if game has multiple paths stored in JSON array
        elif game.save_file_locations and isinstance(game.save_file_locations, list) and len(game.save_file_locations) > 1:
            # Game has multiple paths - use them directly
            save_paths = [path.strip() for path in game.save_file_locations if path and path.strip()]
            if not save_paths:
                return json_response_error('Game has invalid save file locations', status=400)
        else:
            # Single path (existing behavior) - no path_index
            local_save_path, error_response = get_local_save_path_or_error(data, game)
            if error_response:
                return error_response
            
            from SaveNLoad.models.save_folder import SaveFolder
            save_folder = SaveFolder.get_or_create_next(user, game)
            save_folder, error_response = validate_save_folder_or_error(save_folder)
            if error_response:
                return error_response
            
            # Build complete remote FTP path on server
            remote_ftp_path = _build_full_remote_path(
                username=user.username,
                game_name=game.name,
                save_folder_number=save_folder.folder_number,
                path_index=None
            )
            
            operation_id = create_operation(
                {
                    'operation_type': OperationType.SAVE,
                    'user_id': user.id,
                    'game_id': game.id,
                    'local_save_path': local_save_path,
                    'remote_ftp_path': remote_ftp_path,  # Complete path ready for client
                    'save_folder_number': save_folder.folder_number,
                },
                client_worker
            )
            
            return create_operation_response(
                operation_id,
                client_worker,
                message='Save operation queued',
                extra_data={'save_folder_number': save_folder.folder_number}
            )
    
        # Multiple paths handling (either from request or from game model)
        # Create save folder
        from SaveNLoad.models.save_folder import SaveFolder
        save_folder = SaveFolder.get_or_create_next(user, game)
        save_folder, error_response = validate_save_folder_or_error(save_folder)
        if error_response:
            return error_response
        
        # Only use path_index if there are 2+ paths
        use_subfolders = len(save_paths) > 1
        
        # Create operations for each path using path mappings
        operation_ids = []
        for path in save_paths:
            # Validate path is in game's configured paths
            normalized_path = os.path.normpath(path)
            # Ensure save_file_locations is a list
            if not game.save_file_locations:
                return json_response_error('Game has no save file locations configured', status=400)
            if not isinstance(game.save_file_locations, list):
                return json_response_error('Game save file locations is invalid', status=400)
            game_paths = {os.path.normpath(p) for p in game.save_file_locations if p}
            
            if normalized_path not in game_paths:
                return json_response_error(
                    f'Path "{path}" is not configured for this game. Please edit the game to add this path.',
                    status=400
                )
            
            # Get path_index from existing mapping (no auto-creation)
            if use_subfolders:
                path_index = game.get_path_index(path)
                if path_index is None:
                    return json_response_error(
                        f'Path "{path}" is not mapped. Please edit the game to configure path mappings.',
                        status=400
                    )
            else:
                path_index = None
            
            # Build complete remote FTP path on server
            remote_ftp_path = _build_full_remote_path(
                username=user.username,
                game_name=game.name,
                save_folder_number=save_folder.folder_number,
                path_index=path_index
            )
            
            operation_id = create_operation(
                {
                    'operation_type': OperationType.SAVE,
                    'user_id': user.id,
                    'game_id': game.id,
                    'local_save_path': path,
                    'remote_ftp_path': remote_ftp_path,  # Complete path ready for client
                    'save_folder_number': save_folder.folder_number,
                },
                client_worker
            )
            operation_ids.append(operation_id)
        
        return json_response_success(
            message=f'Save operations queued for {len(save_paths)} location(s)',
            data={
                'operation_ids': operation_ids,
                'save_folder_number': save_folder.folder_number,
                'client_id': client_worker,  # client_worker is already a string (client_id)
                'paths_count': len(save_paths)
            }
        )
    except Exception as e:
        import traceback
        print(f"ERROR in save_game: {e}")
        print(traceback.format_exc())
        return json_response_error(f'Failed to save game: {str(e)}', status=500)


@login_required
@require_http_methods(["POST"])
def load_game(request, game_id):
    """
    Load game endpoint - queues operation for client worker
    Expects: {'local_save_path': 'path/to/save/files', 'local_save_paths': ['path1', 'path2'] (optional), 'save_folder_number': 1 (optional), 'client_id': 'optional'}
    
    If local_save_paths is provided, it will load from separate subfolders (path_1, path_2, etc.)
    """
    from SaveNLoad.models.operation_constants import OperationType
    
    user = get_current_user(request)
    
    # Get game or return error
    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response
    
    # Parse JSON body
    data, error_response = parse_json_body(request)
    if error_response:
        return error_response
    
    # Get client worker for this user
    client_worker, error_response = get_client_worker_or_error(user, request)
    if error_response:
        return error_response
    
    save_folder_number = data.get('save_folder_number')
    
    # Get the save folder
    if save_folder_number is None:
        save_folder, error_response = get_latest_save_folder_or_error(user, game)
        if error_response:
            return error_response
        save_folder_number = save_folder.folder_number
    else:
        save_folder, error_response = get_save_folder_or_error(user, game, save_folder_number)
        if error_response:
            return error_response
    
    # Check if multiple paths are provided OR if game has multiple paths
    # First check if explicit paths are provided in request
    if 'local_save_paths' in data:
        # Handle multiple save locations from request
        load_paths, error_response = get_all_save_paths_or_error(data, game, 'local_save_paths')
        if error_response:
            return error_response
    # Check if game has multiple paths stored in JSON array
    elif game.save_file_locations and isinstance(game.save_file_locations, list) and len(game.save_file_locations) > 1:
        # Game has multiple paths - use them directly
        load_paths = [path.strip() for path in game.save_file_locations if path and path.strip()]
        if not load_paths:
            return json_response_error('Game has invalid save file locations', status=400)
    else:
        # Single path (existing behavior) - no path_index
        local_save_path, error_response = get_local_save_path_or_error(data, game)
        if error_response:
            return error_response
        
        # Build complete remote FTP path on server
        remote_ftp_path = _build_full_remote_path(
            username=user.username,
            game_name=game.name,
            save_folder_number=save_folder_number,
            path_index=None
        )
        
        operation_id = create_operation(
            {
                'operation_type': OperationType.LOAD,
                'user_id': user.id,
                'game_id': game.id,
                'local_save_path': local_save_path,
                'remote_ftp_path': remote_ftp_path,
                'save_folder_number': save_folder_number,
            },
            client_worker
        )
        
        return create_operation_response(
            operation_id,
            client_worker,
            message='Load operation queued',
            extra_data={'save_folder_number': save_folder_number}
        )
    
    # Multiple paths handling (either from request or from game model)
    # Only use path_index if there are 2+ paths
    use_subfolders = len(load_paths) > 1
    
    # Create operations for each path using path mappings
    operation_ids = []
    for path in load_paths:
        # Validate path is in game's configured paths
        normalized_path = os.path.normpath(path)
        game_paths = {os.path.normpath(p) for p in game.save_file_locations if p}
        
        if normalized_path not in game_paths:
            return json_response_error(
                f'Path "{path}" is not configured for this game. Please edit the game to add this path.',
                status=400
            )
        
        # Get path_index from mapping (or None if not mapped and single path)
        if use_subfolders:
            path_index = game.get_path_index(path)
            # If path not mapped, this is an error - can't load without knowing which server path
            if path_index is None:
                return json_response_error(
                    f'Path "{path}" is not mapped. Please edit the game to configure path mappings.',
                    status=400
                )
        else:
            path_index = None
        
        # Build complete remote FTP path on server
        remote_ftp_path = _build_full_remote_path(
            username=user.username,
            game_name=game.name,
            save_folder_number=save_folder_number,
            path_index=path_index
        )
        
        operation_id = create_operation(
            {
                'operation_type': OperationType.LOAD,
                'user_id': user.id,
                'game_id': game.id,
                'local_save_path': path,
                'remote_ftp_path': remote_ftp_path,
                'save_folder_number': save_folder_number,
            },
            client_worker
        )
        operation_ids.append(operation_id)
    
    return json_response_success(
        message=f'Load operations queued for {len(load_paths)} location(s)',
        data={
            'operation_ids': operation_ids,
            'save_folder_number': save_folder_number,
            'client_id': client_worker,  # client_worker is already a string (client_id)
            'paths_count': len(load_paths)
        }
    )


@login_required
@require_http_methods(["GET"])
def check_operation_status(request, operation_id):
    """
    Check the status of an operation
    For admin users: can check any operation
    For regular users: can only check their own operations
    
    Special handling: If operation doesn't exist, check if it was a user deletion operation.
    If the user was deleted (CASCADE), the deletion was successful.
    """
    from SaveNLoad.services.redis_operation_service import get_operation, OperationStatus
    from SaveNLoad.models import SimpleUsers
    
    user = get_current_user(request)
    
    # Get operation from Redis
    operation = get_operation(operation_id)
    if not operation:
        # Operation doesn't exist - could be deleted due to CASCADE
        # Check if this might be a user deletion operation by checking recent operations
        # or by checking if any users with pending_deletion were recently deleted
        # For now, return 404 - frontend should handle this gracefully
        # But for user deletion, we can check if any user with pending_deletion was recently deleted
        # Actually, we can't easily determine this without the operation data
        # So we'll return a special response indicating the operation may have completed
        # The frontend will need to handle 404 as a potential success for user deletion
        
        # Try to find if there's a user that was recently deleted (within last minute)
        # This is a workaround - ideally we'd track this differently
        from django.utils import timezone
        from datetime import timedelta
        recent_time = timezone.now() - timedelta(minutes=1)
        
        # Check if admin is checking - if so, return a more helpful response
        is_admin = user.is_admin() if hasattr(user, 'is_admin') else False
        if is_admin:
            # For admin, return a response indicating operation may have completed
            # This is likely a user deletion that completed and CASCADE deleted the operation
            return json_response_success(
                data={
                    'status': OperationStatus.COMPLETED,
                    'completed': True,
                    'failed': False,
                    'message': 'Operation completed (operation record may have been cleaned up)',
                    'result_data': None,
                    'progress': {
                        'current': 1,
                        'total': 1,
                        'percentage': 100,
                        'message': 'Completed'
                    }
                }
            )
        
        # Operation doesn't exist - could be deleted due to CASCADE
        # Check if admin is checking - if so, return a more helpful response
        is_admin = user.is_admin() if hasattr(user, 'is_admin') else False
        if is_admin:
            # For admin, return a response indicating operation may have completed
            # This is likely a user deletion that completed and was cleaned up
            return json_response_success(
                data={
                    'status': OperationStatus.COMPLETED,
                    'completed': True,
                    'failed': False,
                    'message': 'Operation completed (operation record may have been cleaned up)',
                    'result_data': None,
                    'progress': {
                        'current': 1,
                        'total': 1,
                        'percentage': 100,
                        'message': 'Completed'
                    }
                }
            )
        
        return json_response_error('Operation not found', status=404)
    
    # Check permissions: admins can check any operation, users can only check their own
    is_admin = user.is_admin() if hasattr(user, 'is_admin') else False
    operation_user_id = operation.get('user_id')
    if operation_user_id:
        try:
            operation_user_id = int(operation_user_id)
        except (ValueError, TypeError):
            operation_user_id = None
    
    if not is_admin and operation_user_id and operation_user_id != user.id:
        return json_response_error('Operation not found', status=404)
    
    # Get error message and transform to user-friendly format if needed
    error_message = None
    status = operation.get('status', '')
    if status == OperationStatus.FAILED:
        error_msg = operation.get('error_message', '')
        if error_msg:
            error_message = transform_path_error_message(error_msg, operation.get('type', ''))
    
    # Calculate progress percentage
    progress_current = int(operation.get('progress_current', 0) or 0)
    progress_total = int(operation.get('progress_total', 0) or 0)
    progress_percentage = calculate_progress_percentage(progress_current, progress_total, status)
    
    result_data = None
    if status == OperationStatus.COMPLETED:
        result_data_str = operation.get('result_data')
        if result_data_str:
            try:
                import json
                result_data = json.loads(result_data_str) if isinstance(result_data_str, str) else result_data_str
            except:
                result_data = result_data_str
    
    return json_response_success(
        data={
            'status': status,
            'completed': status == OperationStatus.COMPLETED,
            'failed': status == OperationStatus.FAILED,
            'message': error_message,
            'result_data': result_data,
            'progress': {
                'current': progress_current,
                'total': progress_total,
                'percentage': progress_percentage,
                'message': operation.get('progress_message', '') or ''
            }
        }
    )


@login_required
@require_http_methods(["DELETE"])
def delete_save_folder(request, game_id, folder_number):
    """
    Delete a save folder (from SMB and database)
    """
    user = get_current_user(request)
    
    # Get game or return error
    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response
    
    from SaveNLoad.models.operation_constants import OperationType
    
    try:
        # Get and validate save folder
        save_folder, error_response = get_save_folder_or_error(user, game, folder_number)
        if error_response:
            return error_response
        
        # Get client worker for this user (from session - automatic association)
        client_worker, error_response = get_client_worker_or_error(user, request)
        if error_response:
            return error_response
        
        # All validations passed - create DELETE operation
        # Build complete remote FTP path on server
        remote_ftp_path = _build_full_remote_path(
            username=user.username,
            game_name=game.name,
            save_folder_number=folder_number,
            path_index=None
        )
        
        operation_id = create_operation(
            {
                'operation_type': OperationType.DELETE,
                'user_id': user.id,
                'game_id': game.id,
                'local_save_path': '',
                'remote_ftp_path': remote_ftp_path,
                'save_folder_number': folder_number,
            },
            client_worker
        )
        
        # Return operation_id immediately - frontend will poll for status
        # Save folder will be deleted from database when operation completes successfully
        return create_operation_response(
            operation_id,
            client_worker,
            message='Delete operation queued',
            extra_data={'save_folder_number': folder_number}
        )
        
    except Exception as e:
        print(f"ERROR: Failed to delete save folder: {e}")
        return json_response_error(f'Failed to delete save folder: {str(e)}', status=500)


@login_required
@require_http_methods(["GET"])
def list_save_folders(request, game_id):
    """
    List all available save folders for a game with their dates (sorted by latest)
    """
    user = get_current_user(request)
    
    # Get game or return error
    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response
    
    from SaveNLoad.models.save_folder import SaveFolder
    from SaveNLoad.utils.model_utils import filter_by_user_and_game
    
    # Get all save folders for this user+game, sorted by latest first
    save_folders = filter_by_user_and_game(SaveFolder, user, game).order_by('-created_at')
    
    folders_data = []
    for folder in save_folders:
        folders_data.append({
            'folder_number': folder.folder_number,
            'folder_name': folder.folder_name,
            'created_at': to_isoformat(folder.created_at),
            'updated_at': to_isoformat(folder.updated_at)
        })
    
    return json_response_success(
        data={'save_folders': folders_data}
    )


@login_required
@require_http_methods(["GET"])
def list_saves(request, game_id):
    """
    List all available saves for a game - uses client worker
    """
    from SaveNLoad.models.operation_constants import OperationType
    from SaveNLoad.models.save_folder import SaveFolder
    
    user = get_current_user(request)
    
    # Get game or return error
    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response
    
    save_folder_number = request.GET.get('save_folder_number')
    if save_folder_number:
        try:
            save_folder_number = int(save_folder_number)
        except ValueError:
            save_folder_number = None
    
    # If no save_folder_number, use latest
    if save_folder_number is None:
        save_folder, error_response = get_latest_save_folder_or_error(user, game)
        if error_response:
            return error_response
        save_folder_number = save_folder.folder_number
    else:
        # Get specific save folder
        save_folder, error_response = get_save_folder_or_error(user, game, save_folder_number)
        if error_response:
            return error_response
    
    # Get client worker for this user (from session - automatic association)
    client_worker, error_response = get_client_worker_or_error(user, request)
    if error_response:
        return error_response
    
    try:
        # All validations passed - create LIST operation
        # Build complete remote FTP path on server
        remote_ftp_path = _build_full_remote_path(
            username=user.username,
            game_name=game.name,
            save_folder_number=save_folder_number,
            path_index=None
        )
        
        operation_id = create_operation(
            {
                'operation_type': OperationType.LIST,
                'user_id': user.id,
                'game_id': game.id,
                'local_save_path': '',
                'remote_ftp_path': remote_ftp_path,
                'save_folder_number': save_folder_number,
            },
            client_worker
        )
        
        # Wait for operation to be picked up and completed (poll with timeout)
        from SaveNLoad.services.redis_operation_service import get_operation
        import time
        timeout = 30  # 30 seconds timeout
        start_time = time.time()
        
        # Wait for operation to move from PENDING to IN_PROGRESS to COMPLETED/FAILED
        while True:
            if time.time() - start_time > timeout:
                return json_response_error('List operation timed out', status=504)
            time.sleep(0.5)
            operation = get_operation(operation_id)
            if not operation:
                return json_response_error('Operation not found', status=404)
            status = operation.get('status', '')
            if status == 'completed':
                result_data = operation.get('result_data')
                if isinstance(result_data, str):
                    import json
                    result_data = json.loads(result_data) if result_data else {}
                files = result_data.get('files', []) if result_data else []
                message = result_data.get('message', 'List completed') if result_data else 'List completed'
                return json_response_success(
                    data={'files': files, 'message': message}
                )
            elif status == 'failed':
                error_msg = operation.get('error_message', 'List operation failed')
                return json_response_error(error_msg, status=500)
            elif status not in ['pending', 'in_progress']:
                return json_response_error('List operation failed', status=500)
        
    except Exception as e:
        print(f"ERROR: List saves failed: {e}")
        return json_response_error(f'List saves failed: {str(e)}', status=500)


@login_required
@require_http_methods(["GET"])
def backup_all_saves(request, game_id):
    """
    Backup all save files for a game - queues operation for client worker
    """
    from SaveNLoad.models.operation_constants import OperationType
    
    user = get_current_user(request)
    
    # Get game or return error
    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response
    
    # Get client worker for this user (from session - automatic association)
    client_worker, error_response = get_client_worker_or_error(user, request)
    if error_response:
        return error_response
    
    # Create backup operation in queue
    # Backup doesn't need local_save_path or save_folder_number, but we need to provide remote path base
    # Build base path for all game saves (username/gamename)
    safe_game_name = "".join(c for c in game.name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_game_name = safe_game_name.replace(' ', '_')
    remote_ftp_path = f"{user.username}/{safe_game_name}"
    
    operation_id = create_operation(
        {
            'operation_type': OperationType.BACKUP,
            'user_id': user.id,
            'game_id': game.id,
            'local_save_path': '',
            'remote_ftp_path': remote_ftp_path,
            'save_folder_number': None,
        },
        client_worker
    )
    
    return create_operation_response(
        operation_id,
        client_worker,
        message='Backup operation queued'
    )


@login_required
@require_http_methods(["DELETE"])
def delete_all_saves(request, game_id):
    """
    Delete all save folders for a game (from SMB and database)
    """
    user = get_current_user(request)
    
    # Get game or return error
    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response
    
    from SaveNLoad.models.operation_constants import OperationType
    from SaveNLoad.utils.model_utils import filter_by_user_and_game
    
    try:
        # Get all save folders for this user and game
        save_folders = filter_by_user_and_game(SaveFolder, user, game)
        
        if not save_folders.exists():
            return json_response_error('No save folders found for this game', status=404)
        
        # Get client worker for this user (from session - automatic association)
        client_worker, error_response = get_client_worker_or_error(user, request)
        if error_response:
            return error_response
        
        # Create DELETE operations for all save folders
        operation_ids = []
        invalid_folders = []
        
        for save_folder in save_folders:
            try:
                # Validate save folder has required information
                validated_folder, error_response = validate_save_folder_or_error(save_folder)
                if error_response:
                    print(f'WARNING: Save folder {save_folder.id} validation failed: {error_response.content.decode() if hasattr(error_response, "content") else "validation error"}, skipping')
                    invalid_folders.append(save_folder)
                    continue
                
                # Create DELETE operation (will be processed by client worker)
                # Build complete remote FTP path on server
                remote_ftp_path = _build_full_remote_path(
                    username=user.username,
                    game_name=game.name,
                    save_folder_number=save_folder.folder_number,
                    path_index=None
                )
                
                operation_id = create_operation(
                    {
                        'operation_type': OperationType.DELETE,
                        'user_id': user.id,
                        'game_id': game.id,
                        'local_save_path': '',
                        'remote_ftp_path': remote_ftp_path,
                        'save_folder_number': save_folder.folder_number,
                    },
                    client_worker
                )
                operation_ids.append(operation_id)
                    
            except Exception as e:
                print(f"ERROR: Failed to create delete operation for save folder {save_folder.folder_number}: {e}")
                invalid_folders.append(save_folder)
        
        # Delete invalid folders from database immediately
        for save_folder in invalid_folders:
            try:
                save_folder.delete()
            except:
                pass
        
        if not operation_ids:
            if invalid_folders:
                return json_response_error('No valid save folders found to delete', status=404)
            return json_response_error('No save folders found for this game', status=404)
        
        # Return operation IDs - frontend will poll for status
        # Save folders will be deleted from database when operations complete successfully
        return json_response_success(
            message=f'Delete operations queued for {len(operation_ids)} save folder(s)',
            data={
                'operation_ids': operation_ids,
                'total_count': len(operation_ids),
                'client_id': client_worker  # client_worker is already a string (client_id)
            }
        )
        
    except Exception as e:
        print(f"ERROR: Failed to delete all saves: {e}")
        return json_response_error(f'Failed to delete all saves: {str(e)}', status=500)


@login_required
@require_http_methods(["GET"])
def get_game_save_location(request, game_id):
    """
    Get the save file location for a game
    """
    user = get_current_user(request)
    
    # Get game or return error
    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response
    
    # Return first path for backward compatibility, or all paths
    save_paths = game.save_file_locations if isinstance(game.save_file_locations, list) else []
    return json_response_success(
        data={
            'save_file_location': save_paths[0] if save_paths else '',
            'save_file_locations': save_paths,
            'game_name': game.name
        }
    )


@login_required
@require_http_methods(["POST"])
def open_save_location(request, game_id):
    """
    Open the save file location for a game - queues operation for client worker
    Creates local folders if they don't exist, then opens them
    Handles multiple save paths by opening all of them
    """
    from SaveNLoad.models.operation_constants import OperationType
    import json
    
    user = get_current_user(request)
    
    # Get game or return error
    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response
    
    # Get client worker for this user (from session - automatic association)
    client_worker, error_response = get_client_worker_or_error(user, request)
    if error_response:
        return error_response
    
    # Get all save paths for opening folders
    save_paths = game.save_file_locations if isinstance(game.save_file_locations, list) and len(game.save_file_locations) > 0 else []
    
    if not save_paths:
        return json_response_error('No save file location found for this game', status=400)
    
    # Store all paths as JSON string for multi-path support
    # Include flag to create folders if they don't exist
    paths_data = {
        'paths': save_paths,
        'create_folders': True  # Flag to create local folders if they don't exist
    }
    paths_json = json.dumps(paths_data)
    
    # Create open folder operation in queue
    operation_id = create_operation(
        {
            'operation_type': OperationType.OPEN_FOLDER,
            'user_id': user.id,
            'game_id': game.id,
            'local_save_path': paths_json,
            'save_folder_number': None,
            'smb_path': None,
            'path_index': None
        },
        client_worker
    )
    
    # Create message indicating how many folders will be opened
    path_count = len(save_paths)
    message = f'Open folder operation queued ({path_count} location{"s" if path_count > 1 else ""})'
    
    return create_operation_response(
        operation_id,
        client_worker,
        message=message
    )