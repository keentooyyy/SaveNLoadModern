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
from SaveNLoad.workers import FTPWorker
import json
import os
import logging
import ftplib
import ftputil
import zipfile
import tempfile
import io
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)


def _delete_directory_recursive(ftp: ftplib.FTP, current_path: str):
    """Recursively delete all files and subdirectories in the current FTP directory"""
    items = []
    ftp.retrlines('LIST', items.append)
    
    for item_info in items:
        parts = item_info.split()
        if len(parts) >= 9:
            name = ' '.join(parts[8:]) if len(parts) > 8 else parts[-1]
            # Skip . and ..
            if name in ('.', '..'):
                continue
            
            if item_info.startswith('d'):
                # It's a directory - recursively delete it
                try:
                    ftp.cwd(name)
                    _delete_directory_recursive(ftp, f"{current_path}/{name}")
                    ftp.cwd('..')
                    ftp.rmd(name)
                    logger.info(f"Deleted directory {name} from {current_path}")
                except ftplib.error_perm as e:
                    logger.warning(f"Could not delete directory {name}: {e}")
            else:
                # It's a file - delete it
                try:
                    ftp.delete(name)
                    logger.info(f"Deleted file {name} from {current_path}")
                except ftplib.error_perm as e:
                    logger.warning(f"Could not delete file {name}: {e}")


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
    
    # Get client worker or return error
    client_id = data.get('client_id')
    client_worker, error_response = get_client_worker_or_error(client_id)
    if error_response:
        return error_response
    
    # Get or create next save folder (tracked in database)
    from SaveNLoad.models.save_folder import SaveFolder
    save_folder = SaveFolder.get_or_create_next(user, game)
    
    # Create operation in queue with save folder number
    operation = OperationQueue.create_operation(
        operation_type=OperationType.SAVE,
        user=user,
        game=game,
        local_save_path=local_save_path,
        save_folder_number=save_folder.folder_number,
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
    
    # If no save_folder_number specified, use the latest one
    if save_folder_number is None:
        from SaveNLoad.models.save_folder import SaveFolder
        latest_folder = SaveFolder.get_latest(user, game)
        if latest_folder:
            save_folder_number = latest_folder.folder_number
    
    # Get client worker or return error
    client_id = data.get('client_id')
    client_worker, error_response = get_client_worker_or_error(client_id)
    if error_response:
        return error_response
    
    # Create operation in queue
    operation = OperationQueue.create_operation(
        operation_type=OperationType.LOAD,
        user=user,
        game=game,
        local_save_path=local_save_path,
        save_folder_number=save_folder_number,
        client_worker=client_worker
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Load operation queued',
        'operation_id': operation.id,
        'client_id': client_worker.client_id
    })
    
    try:
        worker = FTPWorker()
        
        # List all files in the save folder
        success, files, message = worker.list_saves(
            username=user.username,
            game_name=game.name,
            save_folder_number=save_folder_number
        )
        
        if not success or not files:
            return JsonResponse({
                'success': False,
                'error': f'No save files found: {message}'
            }, status=404)
        
        # Download all files
        downloaded_files = []
        failed_files = []
        
        # Ensure local directory exists
        if os.path.isdir(local_save_path) or not os.path.exists(local_save_path):
            os.makedirs(local_save_path, exist_ok=True)
        
        for file_info in files:
            remote_filename = file_info['name']
            # If local path is a directory, use the filename
            # If local path is a file, use it directly (for single file saves)
            if os.path.isdir(local_save_path):
                local_file = os.path.join(local_save_path, remote_filename)
                # Handle nested paths
                if '/' in remote_filename:
                    nested_dir = os.path.join(local_save_path, os.path.dirname(remote_filename))
                    os.makedirs(nested_dir, exist_ok=True)
            else:
                local_file = local_save_path
            
            success, message = worker.download_save(
                username=user.username,
                game_name=game.name,
                remote_filename=remote_filename,
                local_file_path=local_file,
                save_folder_number=save_folder_number
            )
            
            if success:
                downloaded_files.append(remote_filename)
            else:
                failed_files.append({'file': remote_filename, 'error': message})
        
        if failed_files:
            return JsonResponse({
                'success': False,
                'message': f'Downloaded {len(downloaded_files)} file(s), {len(failed_files)} failed',
                'downloaded_files': downloaded_files,
                'failed_files': failed_files
            }, status=207)  # Multi-Status
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully downloaded {len(downloaded_files)} file(s)',
            'downloaded_files': downloaded_files
        })
                
    except Exception as e:
        logger.error(f"Load operation failed: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Load operation failed: {str(e)}'
        }, status=500)


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
    
    return json_response_success(
        data={
            'status': operation.status,
            'completed': operation.status == OperationStatus.COMPLETED,
            'failed': operation.status == OperationStatus.FAILED,
            'message': operation.error_message if operation.status == OperationStatus.FAILED else None,
            'result_data': operation.result_data if operation.status == OperationStatus.COMPLETED else None
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
    from SaveNLoad.workers import FTPWorker
    
    try:
        # Get the save folder from database
        save_folder = SaveFolder.get_by_number(user, game, folder_number)
        if not save_folder:
            return json_response_error('Save folder not found', status=404)
        
        # Delete from FTP server
        worker = FTPWorker()
        base_path = worker._get_user_game_path(user.username, game.name)
        save_folder_name = f"save_{folder_number}"
        
        ftp = None
        ftp_deletion_success = True
        try:
            ftp = worker._get_connection()
            save_folder_path = f"{base_path}/{save_folder_name}"
            
            # Navigate to base path
            try:
                ftp.cwd(base_path)
            except ftplib.error_perm:
                # Base path doesn't exist, nothing to delete - this is fine
                logger.info(f"Base path {base_path} doesn't exist on FTP, nothing to delete")
            else:
                # Recursively delete all files and subdirectories in the save folder
                try:
                    ftp.cwd(save_folder_name)
                    _delete_directory_recursive(ftp, save_folder_path)
                    
                    # Go back to base path and delete the folder itself
                    ftp.cwd('..')
                    try:
                        ftp.rmd(save_folder_name)
                        logger.info(f"Deleted save folder {save_folder_name}")
                    except ftplib.error_perm as e:
                        logger.warning(f"Could not delete folder {save_folder_name}: {e}")
                        ftp_deletion_success = False
                except ftplib.error_perm:
                    # Folder doesn't exist on FTP, that's okay
                    logger.info(f"Save folder {save_folder_name} doesn't exist on FTP")
            
        except Exception as e:
            logger.error(f"Failed to delete save folder from FTP: {e}")
            ftp_deletion_success = False
        finally:
            if ftp:
                try:
                    ftp.quit()
                except:
                    try:
                        ftp.close()
                    except:
                        pass
        
        # Delete from database
        save_folder.delete()
        
        # Return appropriate message based on FTP deletion success
        if ftp_deletion_success:
            return json_response_success(
                message=f'Save folder {folder_number} deleted successfully'
            )
        else:
            return json_response_success(
                message=f'Save folder {folder_number} deleted (some FTP cleanup may have failed)'
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
    List all available saves for a game
    """
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
    
    try:
        worker = FTPWorker()
        success, files, message = worker.list_saves(
            username=user.username,
            game_name=game.name,
            save_folder_number=save_folder_number
        )
        
        if not success:
            return json_response_error(message, status=500)
        
        return json_response_success(
            data={'files': files, 'message': message}
        )
        
    except Exception as e:
        logger.error(f"List saves failed: {e}")
        return json_response_error(f'List saves failed: {str(e)}', status=500)


@login_required
@require_http_methods(["GET"])
def backup_all_saves(request, game_id):
    """
    Backup all save files for a game into a zip file
    Downloads all files from all save folders and creates a zip archive
    """
    user = get_current_user(request)
    if not user:
        return json_response_error('Unauthorized', status=403)
    
    # Get game or return error
    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response
    
    # Create a temporary zip file in memory
    zip_buffer = io.BytesIO()
    
    try:
        worker = FTPWorker()
        base_path = worker._get_user_game_path(user.username, game.name)
        
        # Use ftputil for more robust FTP operations
        ftp_host = getattr(settings, 'FTP_HOST', None)
        ftp_port = getattr(settings, 'FTP_PORT', None)
        ftp_username = getattr(settings, 'FTP_USERNAME', None)
        ftp_password = getattr(settings, 'FTP_PASSWORD', None)
        
        if not all([ftp_host, ftp_port, ftp_username, ftp_password]):
            return json_response_error('FTP credentials not configured', status=500)
        
        # Create ftputil session
        # ftputil.FTPHost doesn't accept port directly, use session factory for custom port
        if ftp_port != 21:
            session_factory = ftputil.session.session_factory(port=ftp_port)
            ftp_host_obj = ftputil.FTPHost(ftp_host, ftp_username, ftp_password, session_factory=session_factory)
        else:
            ftp_host_obj = ftputil.FTPHost(ftp_host, ftp_username, ftp_password)
        
        try:
            # Check if base path exists
            full_base_path = f"/{base_path}"
            if not ftp_host_obj.path.exists(full_base_path):
                return json_response_error(f'Game directory not found on server: {base_path}', status=404)
            
            # List all save folders in base path
            try:
                ftp_host_obj.chdir(full_base_path)
                items = ftp_host_obj.listdir('.')
                
                # Filter for save folders (save_1, save_2, etc.)
                existing_save_folders = []
                for item in items:
                    item_path = ftp_host_obj.path.join(full_base_path, item)
                    if ftp_host_obj.path.isdir(item_path) and item.startswith('save_') and item[5:].isdigit():
                        existing_save_folders.append(item)
                
                # Sort by number
                existing_save_folders.sort(key=lambda x: int(x.split('_')[1]))
                
                if not existing_save_folders:
                    return json_response_error('No save folders found on server', status=404)
                
            except Exception as e:
                return json_response_error(f'Failed to access game directory: {str(e)}', status=500)
            
            # Create zip file using ftputil for robust file operations
            files_added = 0
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Iterate through each save folder that exists on FTP
                for save_folder_name in existing_save_folders:
                    save_folder_path = ftp_host_obj.path.join(full_base_path, save_folder_name)
                    
                    try:
                        # Check if save folder exists and is a directory
                        if not ftp_host_obj.path.exists(save_folder_path) or not ftp_host_obj.path.isdir(save_folder_path):
                            continue
                        
                        # Change to save folder
                        ftp_host_obj.chdir(save_folder_path)
                        
                        # List all files in this folder (recursively)
                        def list_files_recursive(current_path, base_path):
                            """Recursively list all files in a directory"""
                            files = []
                            try:
                                for item in ftp_host_obj.listdir(current_path):
                                    item_path = ftp_host_obj.path.join(current_path, item)
                                    if ftp_host_obj.path.isfile(item_path):
                                        # Get relative path by removing base_path prefix
                                        if item_path.startswith(base_path):
                                            rel_path = item_path[len(base_path):].lstrip('/')
                                        else:
                                            rel_path = item
                                        files.append(rel_path)
                                    elif ftp_host_obj.path.isdir(item_path):
                                        # Recursively get files from subdirectories
                                        files.extend(list_files_recursive(item_path, base_path))
                            except Exception:
                                pass
                            return files
                        
                        all_files = list_files_recursive(save_folder_path, save_folder_path)
                        
                        if not all_files:
                            continue
                        
                        # Download each file
                        for filename in all_files:
                            try:
                                # Use ftputil to download file to memory
                                file_data = io.BytesIO()
                                with ftp_host_obj.open(filename, 'rb') as remote_file:
                                    file_data.write(remote_file.read())
                                
                                file_data.seek(0)
                                
                                # Add to zip with folder structure: save_1/filename, save_2/filename, etc.
                                # Handle nested paths (replace backslashes with forward slashes for zip)
                                zip_path = f"{save_folder_name}/{filename.replace(chr(92), '/')}"
                                zip_file.writestr(zip_path, file_data.read())
                                files_added += 1
                            except Exception:
                                continue
                    
                    except Exception:
                        continue
        finally:
            ftp_host_obj.close()
        
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

