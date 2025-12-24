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
import json
import os
import zipfile
import tempfile
import io
from pathlib import Path
from django.conf import settings


@login_required
@require_http_methods(["POST"])
def save_game(request, game_id):
    """
    Save game endpoint - queues operation for client worker
    Expects: {'local_save_path': 'path/to/save/files', 'local_save_paths': ['path1', 'path2'] (optional), 'client_id': 'optional'}
    
    If local_save_paths is provided, it will save all locations to separate subfolders (path_1, path_2, etc.)
    """
    from SaveNLoad.models.client_worker import ClientWorker
    from SaveNLoad.models.operation_queue import OperationQueue, OperationType
    
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
        
        operation = OperationQueue.create_operation(
            operation_type=OperationType.SAVE,
            user=user,
            game=game,
            local_save_path=local_save_path,
            save_folder_number=save_folder.folder_number,
            smb_path=save_folder.smb_path,
            client_worker=client_worker,
            path_index=None  # No subfolder for single path
        )
        
        return create_operation_response(
            operation,
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
        
        operation = OperationQueue.create_operation(
            operation_type=OperationType.SAVE,
            user=user,
            game=game,
            local_save_path=path,
            save_folder_number=save_folder.folder_number,
            smb_path=save_folder.smb_path,
            client_worker=client_worker,
            path_index=path_index
        )
        operation_ids.append(operation.id)
    
    return json_response_success(
        message=f'Save operations queued for {len(save_paths)} location(s)',
        data={
            'operation_ids': operation_ids,
            'save_folder_number': save_folder.folder_number,
            'client_id': client_worker.client_id,
            'paths_count': len(save_paths)
        }
    )


@login_required
@require_http_methods(["POST"])
def load_game(request, game_id):
    """
    Load game endpoint - queues operation for client worker
    Expects: {'local_save_path': 'path/to/save/files', 'local_save_paths': ['path1', 'path2'] (optional), 'save_folder_number': 1 (optional), 'client_id': 'optional'}
    
    If local_save_paths is provided, it will load from separate subfolders (path_1, path_2, etc.)
    """
    from SaveNLoad.models.client_worker import ClientWorker
    from SaveNLoad.models.operation_queue import OperationQueue, OperationType
    
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
        
        operation = OperationQueue.create_operation(
            operation_type=OperationType.LOAD,
            user=user,
            game=game,
            local_save_path=local_save_path,
            save_folder_number=save_folder_number,
            smb_path=save_folder.smb_path,
            client_worker=client_worker,
            path_index=None  # No subfolder for single path
        )
        
        return create_operation_response(
            operation,
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
        
        operation = OperationQueue.create_operation(
            operation_type=OperationType.LOAD,
            user=user,
            game=game,
            local_save_path=path,
            save_folder_number=save_folder_number,
            smb_path=save_folder.smb_path,
            client_worker=client_worker,
            path_index=path_index
        )
        operation_ids.append(operation.id)
    
    return json_response_success(
        message=f'Load operations queued for {len(load_paths)} location(s)',
        data={
            'operation_ids': operation_ids,
            'save_folder_number': save_folder_number,
            'client_id': client_worker.client_id,
            'paths_count': len(load_paths)
        }
    )


@login_required
@require_http_methods(["GET"])
def check_operation_status(request, operation_id):
    """
    Check the status of an operation
    """
    from SaveNLoad.models.operation_queue import OperationQueue, OperationStatus
    
    user = get_current_user(request)
    
    # Get operation or return error
    from SaveNLoad.views.api_helpers import get_operation_or_error
    operation, error_response = get_operation_or_error(operation_id, user)
    if error_response:
        return error_response
    
    # Get error message and transform to user-friendly format if needed
    error_message = None
    if operation.status == OperationStatus.FAILED and operation.error_message:
        error_message = transform_path_error_message(operation.error_message, operation.operation_type)
    
    # Calculate progress percentage
    progress_percentage = calculate_progress_percentage(
        operation.progress_current,
        operation.progress_total,
        operation.status
    )
    
    return json_response_success(
        data={
            'status': operation.status,
            'completed': operation.status == OperationStatus.COMPLETED,
            'failed': operation.status == OperationStatus.FAILED,
            'message': error_message,
            'result_data': operation.result_data if operation.status == OperationStatus.COMPLETED else None,
            'progress': {
                'current': operation.progress_current,
                'total': operation.progress_total,
                'percentage': progress_percentage,
                'message': operation.progress_message or ''
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
    
    from SaveNLoad.models.operation_queue import OperationQueue, OperationType
    
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
        operation = OperationQueue.create_operation(
            operation_type=OperationType.DELETE,
            user=user,
            game=game,
            local_save_path='',  # Not needed for delete
            save_folder_number=folder_number,
            smb_path=save_folder.smb_path,
            client_worker=client_worker
        )
        
        # Return operation_id immediately - frontend will poll for status
        # Save folder will be deleted from database when operation completes successfully
        return create_operation_response(
            operation,
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
    from SaveNLoad.models.client_worker import ClientWorker
    from SaveNLoad.models.operation_queue import OperationQueue, OperationType, OperationStatus
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
        # All validations passed - create LIST operation (with client_worker set but status PENDING)
        operation = OperationQueue.create_operation(
            operation_type=OperationType.LIST,
            user=user,
            game=game,
            local_save_path='',  # Not needed for list
            save_folder_number=save_folder_number,
            smb_path=save_folder.smb_path,
            client_worker=client_worker
        )
        
        # Wait for operation to be picked up and completed (poll with timeout)
        import time
        timeout = 30  # 30 seconds timeout
        start_time = time.time()
        
        # Wait for operation to move from PENDING to IN_PROGRESS to COMPLETED/FAILED
        while operation.status in [OperationStatus.PENDING, OperationStatus.IN_PROGRESS]:
            if time.time() - start_time > timeout:
                return json_response_error('List operation timed out', status=504)
            time.sleep(0.5)
            operation.refresh_from_db()
        
        if operation.status == OperationStatus.COMPLETED:
            result_data = operation.result_data or {}
            files = result_data.get('files', [])
            message = result_data.get('message', 'List completed')
            return json_response_success(
                data={'files': files, 'message': message}
            )
        else:
            error_msg = operation.error_message or 'List operation failed'
            return json_response_error(error_msg, status=500)
        
    except Exception as e:
        print(f"ERROR: List saves failed: {e}")
        return json_response_error(f'List saves failed: {str(e)}', status=500)


@login_required
@require_http_methods(["GET"])
def backup_all_saves(request, game_id):
    """
    Backup all save files for a game - queues operation for client worker
    """
    from SaveNLoad.models.client_worker import ClientWorker
    from SaveNLoad.models.operation_queue import OperationQueue, OperationType
    
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
    # Backup doesn't need local_save_path or save_folder_number, but we need to provide local_save_path
    # Use a placeholder since backup saves to Downloads folder
    operation = OperationQueue.create_operation(
        operation_type=OperationType.BACKUP,
        user=user,
        game=game,
        local_save_path='',  # Not used for backup
        save_folder_number=None,  # Not used for backup
        smb_path=None,  # Not used for backup
        client_worker=client_worker
    )
    
    return create_operation_response(
        operation,
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
    
    from SaveNLoad.models.operation_queue import OperationQueue, OperationType
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
                operation = OperationQueue.create_operation(
                    operation_type=OperationType.DELETE,
                    user=user,
                    game=game,
                    local_save_path='',  # Not needed for delete
                    save_folder_number=save_folder.folder_number,
                    smb_path=save_folder.smb_path,
                    client_worker=client_worker
                )
                operation_ids.append(operation.id)
                    
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
                'client_id': client_worker.client_id
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
    Handles multiple save paths by opening all of them
    """
    from SaveNLoad.models.client_worker import ClientWorker
    from SaveNLoad.models.operation_queue import OperationQueue, OperationType
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
    # Client worker will parse this and open all folders
    paths_json = json.dumps(save_paths)
    
    # Create open folder operation in queue
    operation = OperationQueue.create_operation(
        operation_type=OperationType.OPEN_FOLDER,
        user=user,
        game=game,
        local_save_path=paths_json,  # Store JSON array of paths
        save_folder_number=None,  # Not used for open folder
        smb_path=None,  # Not used for open folder
        client_worker=client_worker
    )
    
    # Create message indicating how many folders will be opened
    path_count = len(save_paths)
    message = f'Open folder operation queued ({path_count} location{"s" if path_count > 1 else ""})'
    
    return create_operation_response(
        operation,
        client_worker,
        message=message
    )