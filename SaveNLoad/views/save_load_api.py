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
    json_response_error,
    json_response_success
)
from SaveNLoad.models import Game
import json
import os
import logging
import zipfile
import tempfile
import io
from pathlib import Path
from django.conf import settings
from SaveNLoad.utils.smb_storage import get_smb_storage

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def save_game(request, game_id):
    """
    Save game endpoint - queues operation for client worker
    Expects: {'local_save_path': 'path/to/save/files', 'client_id': 'optional'}
    """
    from SaveNLoad.models.client_worker import ClientWorker
    from SaveNLoad.models.operation_queue import OperationQueue, OperationType
    
    user = get_current_user(request)
    if not user:
        return json_response_error('Unauthorized', status=403)
    
    # Get game or return error
    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response
    
    # Parse JSON body
    data, error_response = parse_json_body(request)
    if error_response:
        return error_response
    
    local_save_path = data.get('local_save_path', '').strip()
    if not local_save_path:
        # Use the game's save_file_location if not provided
        local_save_path = game.save_file_location
    
    # Validate local_save_path is provided (actual existence check happens on client worker)
    if not local_save_path or not local_save_path.strip():
        return json_response_error('Local save path is required', status=400)
    
    # Get client worker or return error
    client_id = data.get('client_id')
    client_worker, error_response = get_client_worker_or_error(client_id)
    if error_response:
        return error_response
    
    # Only create save folder after all validations pass
    # Note: We can't validate local path exists on server (it's on client machine)
    # Client worker will validate and report back if path doesn't exist
    from SaveNLoad.models.save_folder import SaveFolder
    save_folder = SaveFolder.get_or_create_next(user, game)
    
    # Validate save folder has required information
    if not save_folder or not save_folder.folder_number:
        return json_response_error('Failed to create save folder', status=500)
    
    if not save_folder.ftp_path:
        return json_response_error('Save folder path is missing', status=500)
    
    # All validations passed - create operation in queue with save folder number and SMB path
    operation = OperationQueue.create_operation(
        operation_type=OperationType.SAVE,
        user=user,
        game=game,
        local_save_path=local_save_path,
        save_folder_number=save_folder.folder_number,
        ftp_path=save_folder.ftp_path,
        client_worker=client_worker
    )
    
    return json_response_success(
        message='Save operation queued',
        data={
            'operation_id': operation.id,
            'client_id': client_worker.client_id,
            'save_folder_number': save_folder.folder_number
        }
    )


@login_required
@require_http_methods(["POST"])
def load_game(request, game_id):
    """
    Load game endpoint - queues operation for client worker
    Expects: {'local_save_path': 'path/to/save/files', 'save_folder_number': 1 (optional), 'client_id': 'optional'}
    """
    from SaveNLoad.models.client_worker import ClientWorker
    from SaveNLoad.models.operation_queue import OperationQueue, OperationType
    
    user = get_current_user(request)
    if not user:
        return json_response_error('Unauthorized', status=403)
    
    # Get game or return error
    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response
    
    # Parse JSON body
    data, error_response = parse_json_body(request)
    if error_response:
        return error_response
    
    local_save_path = data.get('local_save_path', '').strip()
    if not local_save_path:
        # Use the game's save_file_location if not provided
        local_save_path = game.save_file_location
    
    save_folder_number = data.get('save_folder_number')  # Optional
    
    # Validate local_save_path
    if not local_save_path or not local_save_path.strip():
        return json_response_error('Local save path is required', status=400)
    
    # Get the save folder to get ftp_path
    from SaveNLoad.models.save_folder import SaveFolder
    save_folder = None
    if save_folder_number is None:
        # If no save_folder_number specified, use the latest one
        save_folder = SaveFolder.get_latest(user, game)
        if save_folder:
            save_folder_number = save_folder.folder_number
        else:
            # No save folders exist for this game
            return json_response_error('No save files found to load', status=404)
    else:
        # Get the specific save folder
        save_folder = SaveFolder.get_by_number(user, game, save_folder_number)
        if not save_folder:
            return json_response_error('Save folder not found', status=404)
    
    # Validate save_folder_number is set
    if save_folder_number is None:
        return json_response_error('Save folder number is required', status=400)
    
    # Validate save_folder exists and has path
    if not save_folder:
        return json_response_error('Save folder not found', status=404)
    
    if not save_folder.ftp_path:
        return json_response_error('Save folder path is missing', status=500)
    
    # Get client worker or return error
    client_id = data.get('client_id')
    client_worker, error_response = get_client_worker_or_error(client_id)
    if error_response:
        return error_response
    
    # All validations passed - create operation in queue with FTP path
    operation = OperationQueue.create_operation(
        operation_type=OperationType.LOAD,
        user=user,
        game=game,
        local_save_path=local_save_path,
        save_folder_number=save_folder_number,
        ftp_path=save_folder.ftp_path,
        client_worker=client_worker
    )
    
    return json_response_success(
        message='Load operation queued',
        data={
            'operation_id': operation.id,
            'client_id': client_worker.client_id,
            'save_folder_number': save_folder_number
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
    if not user:
        return json_response_error('Unauthorized', status=403)
    
    try:
        operation = OperationQueue.objects.get(pk=operation_id, user=user)
    except OperationQueue.DoesNotExist:
        return json_response_error('Operation not found', status=404)
    
    # Get error message and transform to user-friendly format if needed
    error_message = None
    if operation.status == OperationStatus.FAILED and operation.error_message:
        error_message = operation.error_message
        error_lower = error_message.lower()
        # Transform old error messages to user-friendly format
        if 'local save path does not exist' in error_lower or 'local file not found' in error_lower:
            if operation.operation_type == 'save':
                error_message = 'Oops! You don\'t have any save files to save. Maybe you haven\'t played the game yet, or the save location is incorrect.'
            elif operation.operation_type == 'load':
                error_message = 'Oops! You don\'t have any save files to load. Maybe you haven\'t saved this game yet.'
    
    # Calculate progress percentage
    progress_percentage = 0
    if operation.progress_total > 0:
        progress_percentage = min(100, int((operation.progress_current / operation.progress_total) * 100))
    elif operation.status == OperationStatus.COMPLETED:
        progress_percentage = 100
    elif operation.status == OperationStatus.FAILED:
        progress_percentage = 0
    
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
    Delete a save folder (from FTP and database)
    """
    user = get_current_user(request)
    if not user:
        return json_response_error('Unauthorized', status=403)
    
    # Get game or return error
    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response
    
    from SaveNLoad.models.save_folder import SaveFolder
    from SaveNLoad.models.client_worker import ClientWorker
    from SaveNLoad.models.operation_queue import OperationQueue, OperationType, OperationStatus
    
    try:
        # Get the save folder from database
        save_folder = SaveFolder.get_by_number(user, game, folder_number)
        if not save_folder:
            return json_response_error('Save folder not found', status=404)
        
        # Validate save folder has required information
        if not save_folder.folder_number:
            return json_response_error('Save folder number is missing', status=500)
        
        if not save_folder.ftp_path:
            return json_response_error('Save folder path is missing', status=500)
        
        # Get client worker
        client_worker = ClientWorker.get_any_active_worker()
        if not client_worker:
            return json_response_error('No active client worker available', status=503)
        
        # All validations passed - create DELETE operation (with client_worker set but status PENDING)
        operation = OperationQueue.create_operation(
            operation_type=OperationType.DELETE,
            user=user,
            game=game,
            local_save_path='',  # Not needed for delete
            save_folder_number=folder_number,
            ftp_path=save_folder.ftp_path,
            client_worker=client_worker
        )
        
        # Return operation_id immediately - frontend will poll for status
        # Save folder will be deleted from database when operation completes successfully
        return json_response_success(
            message='Delete operation queued',
            data={
                'operation_id': operation.id,
                'client_id': client_worker.client_id,
                'save_folder_number': folder_number
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to delete save folder: {e}")
        return json_response_error(f'Failed to delete save folder: {str(e)}', status=500)


@login_required
@require_http_methods(["GET"])
def list_save_folders(request, game_id):
    """
    List all available save folders for a game with their dates (sorted by latest)
    """
    user = get_current_user(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return JsonResponse({'error': 'Game not found'}, status=404)
    
    from SaveNLoad.models.save_folder import SaveFolder
    
    # Get all save folders for this user+game, sorted by latest first
    save_folders = SaveFolder.objects.filter(
        user=user,
        game=game
    ).order_by('-created_at')
    
    folders_data = []
    for folder in save_folders:
        folders_data.append({
            'folder_number': folder.folder_number,
            'folder_name': folder.folder_name,
            'created_at': folder.created_at.isoformat(),
            'updated_at': folder.updated_at.isoformat()
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
    if not user:
        return json_response_error('Unauthorized', status=403)
    
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
        latest_folder = SaveFolder.get_latest(user, game)
        if latest_folder:
            save_folder_number = latest_folder.folder_number
        else:
            return json_response_error('No save folders found', status=404)
    
    # Get save folder to get ftp_path
    save_folder = SaveFolder.get_by_number(user, game, save_folder_number)
    if not save_folder:
        return json_response_error('Save folder not found', status=404)
    
    # Validate save folder has required information
    if not save_folder.folder_number:
        return json_response_error('Save folder number is missing', status=500)
    
    if not save_folder.ftp_path:
        return json_response_error('Save folder FTP path is missing', status=500)
    
    # Get client worker
    client_worker = ClientWorker.get_any_active_worker()
    if not client_worker:
        return json_response_error('No active client worker available', status=503)
    
    try:
        # All validations passed - create LIST operation (with client_worker set but status PENDING)
        operation = OperationQueue.create_operation(
            operation_type=OperationType.LIST,
            user=user,
            game=game,
            local_save_path='',  # Not needed for list
            save_folder_number=save_folder_number,
            ftp_path=save_folder.ftp_path,
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
        logger.error(f"List saves failed: {e}")
        return json_response_error(f'List saves failed: {str(e)}', status=500)


@login_required
@require_http_methods(["GET"])
def backup_all_saves(request, game_id):
    """
    Backup all save files for a game into a zip file
    """
    user = get_current_user(request)
    if not user:
        return json_response_error('Unauthorized', status=403)
    
    # Get game or return error
    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response
    
    try:
        # Get SMB storage instance
        smb_storage = get_smb_storage()
        
        # Generate base path for user's game (matching SaveFolder logic)
        safe_game_name = "".join(c for c in game.name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_game_name = safe_game_name.replace(' ', '_')
        base_path = f"/{user.username}/{safe_game_name}"
        
        # Check if base path exists
        if not smb_storage.path_exists(base_path):
            return json_response_error(f'Game directory not found on server: {base_path}', status=404)
        
        # List all save folders in base path
        files_list, dirs_list = smb_storage.list_directory(base_path)
        
        # Filter for save folders (save_1, save_2, etc.)
        existing_save_folders = []
        for item in dirs_list:
            if item.startswith('save_') and item[5:].isdigit():
                existing_save_folders.append(item)
        
        # Sort by number
        existing_save_folders.sort(key=lambda x: int(x.split('_')[1]))
        
        if not existing_save_folders:
            return json_response_error('No save folders found on server', status=404)
        
        # Create zip file using SMB storage
        files_added = 0
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Iterate through each save folder
            for save_folder_name in existing_save_folders:
                save_folder_path = f"{base_path}/{save_folder_name}"
                
                try:
                    # List all files recursively in this save folder
                    all_files, all_dirs = smb_storage.list_recursive(save_folder_path)
                    
                    if not all_files:
                        continue
                    
                    # Download each file and add to zip
                    for file_info in all_files:
                        try:
                            file_path = f"{save_folder_path}/{file_info['name']}"
                            file_data = smb_storage.read_file(file_path)
                            
                            # Add to zip with folder structure: save_1/filename, save_2/filename, etc.
                            zip_path = f"{save_folder_name}/{file_info['name']}"
                            zip_file.writestr(zip_path, file_data)
                            files_added += 1
                        except Exception as e:
                            logger.debug(f"Failed to add file {file_info['name']} to zip: {e}")
                            continue
                
                except Exception as e:
                    logger.debug(f"Failed to process save folder {save_folder_name}: {e}")
                    continue
        
        logger.info(f"Backup complete. Total files added: {files_added}")
        if files_added == 0:
            logger.warning(f"No files were added to backup zip for game {game.name}")
            return json_response_error('No files found in save folders to backup', status=404)
        
        # Prepare zip file for download
        zip_buffer.seek(0)
        
        # Create safe filename
        safe_game_name = "".join(c for c in game.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        zip_filename = f"{safe_game_name}_saves_bak.zip"
        
        # Create HTTP response with zip file
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        response['Content-Length'] = len(zip_buffer.getvalue())
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        return json_response_error(f'Failed to create backup: {str(e)}', status=500)


@login_required
@require_http_methods(["DELETE"])
def delete_all_saves(request, game_id):
    """
    Delete all save folders for a game (from SMB and database)
    """
    user = get_current_user(request)
    if not user:
        return json_response_error('Unauthorized', status=403)
    
    # Get game or return error
    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response
    
    from SaveNLoad.models.save_folder import SaveFolder
    from SaveNLoad.models.client_worker import ClientWorker
    from SaveNLoad.models.operation_queue import OperationQueue, OperationType, OperationStatus
    
    try:
        # Get all save folders for this user and game
        save_folders = SaveFolder.objects.filter(user=user, game=game)
        
        if not save_folders.exists():
            return json_response_error('No save folders found for this game', status=404)
        
        # Get client worker
        client_worker = ClientWorker.get_any_active_worker()
        if not client_worker:
            return json_response_error('No active client worker available', status=503)
        
        # Create DELETE operations for all save folders
        operation_ids = []
        invalid_folders = []
        
        for save_folder in save_folders:
            try:
                # Validate save folder has required information
                if not save_folder.folder_number:
                    logger.warning(f'Save folder {save_folder.id} missing folder_number, skipping')
                    invalid_folders.append(save_folder)
                    continue
                
                if not save_folder.ftp_path:
                    logger.warning(f'Save folder {save_folder.id} missing ftp_path, skipping')
                    invalid_folders.append(save_folder)
                    continue
                
                # Create DELETE operation (will be processed by client worker)
                operation = OperationQueue.create_operation(
                    operation_type=OperationType.DELETE,
                    user=user,
                    game=game,
                    local_save_path='',  # Not needed for delete
                    save_folder_number=save_folder.folder_number,
                    ftp_path=save_folder.ftp_path,
                    client_worker=client_worker
                )
                operation_ids.append(operation.id)
                    
            except Exception as e:
                logger.error(f"Failed to create delete operation for save folder {save_folder.folder_number}: {e}")
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
        logger.error(f"Failed to delete all saves: {e}")
        return json_response_error(f'Failed to delete all saves: {str(e)}', status=500)

