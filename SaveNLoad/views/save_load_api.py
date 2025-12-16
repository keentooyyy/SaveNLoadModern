"""
API endpoints for save/load operations
These endpoints are used by the client worker to perform save/load operations
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from SaveNLoad.views.custom_decorators import login_required, get_current_user
from SaveNLoad.models import Game
from SaveNLoad.workers import FTPWorker
import json
import os
import logging

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
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return JsonResponse({'error': 'Game not found'}, status=404)
    
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)
    
    local_save_path = data.get('local_save_path', '').strip()
    if not local_save_path:
        # Use the game's save_file_location if not provided
        local_save_path = game.save_file_location
    
    # Get or assign client worker
    client_id = data.get('client_id')
    if client_id:
        # Use specified client worker
        client_worker = ClientWorker.get_worker_by_id(client_id)
        if not client_worker:
            return JsonResponse({'error': 'Specified client worker is not online'}, status=400)
    else:
        # Get any available worker
        client_worker = ClientWorker.get_any_active_worker()
        if not client_worker:
            return JsonResponse({
                'error': 'No client worker available',
                'requires_worker': True
            }, status=503)
    
    # Create operation in queue
    operation = OperationQueue.create_operation(
        operation_type=OperationType.SAVE,
        user=user,
        game=game,
        local_save_path=local_save_path,
        client_worker=client_worker
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Save operation queued',
        'operation_id': operation.id,
        'client_id': client_worker.client_id
    })


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
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return JsonResponse({'error': 'Game not found'}, status=404)
    
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)
    
    local_save_path = data.get('local_save_path', '').strip()
    if not local_save_path:
        # Use the game's save_file_location if not provided
        local_save_path = game.save_file_location
    
    save_folder_number = data.get('save_folder_number')  # Optional
    
    # Get or assign client worker
    client_id = data.get('client_id')
    if client_id:
        # Use specified client worker
        client_worker = ClientWorker.get_worker_by_id(client_id)
        if not client_worker:
            return JsonResponse({'error': 'Specified client worker is not online'}, status=400)
    else:
        # Get any available worker
        client_worker = ClientWorker.get_any_active_worker()
        if not client_worker:
            return JsonResponse({
                'error': 'No client worker available',
                'requires_worker': True
            }, status=503)
    
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
def list_saves(request, game_id):
    """
    List all available saves for a game
    """
    user = get_current_user(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return JsonResponse({'error': 'Game not found'}, status=404)
    
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
            return JsonResponse({
                'success': False,
                'error': message
            }, status=500)
        
        return JsonResponse({
            'success': True,
            'files': files,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"List saves failed: {e}")
        return JsonResponse({
            'success': False,
            'error': f'List saves failed: {str(e)}'
        }, status=500)

