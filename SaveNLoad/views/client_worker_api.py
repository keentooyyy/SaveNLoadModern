"""
API endpoints for client worker registration and communication
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from SaveNLoad.models.client_worker import ClientWorker
from SaveNLoad.models import SimpleUsers, Game
from SaveNLoad.views.api_helpers import (
    parse_json_body,
    get_client_worker_by_id_or_error,
    json_response_error,
    json_response_success,
    delete_game_banner_file
)
import json
import os


@csrf_exempt
@require_http_methods(["POST"])
def register_client(request):
    """Register a client worker - client_id must be unique per PC"""
    try:
        data, error_response = parse_json_body(request)
        if error_response:
            return error_response
        
        client_id = data.get('client_id', '').strip()
        
        if not client_id:
            return json_response_error('client_id is required', status=400)
        
        # Create or update client worker
        worker, created = ClientWorker.objects.get_or_create(
            client_id=client_id,
            defaults={
                'is_active': True, 
                'last_heartbeat': timezone.now()
            }
        )
        
        if not created:
            # Update existing worker
            worker.is_active = True
            worker.last_heartbeat = timezone.now()
            worker.save()
        
        # If user is logged in, update their session with this client_id
        # If user is logged out, clear client_id from session (if it exists)
        # This associates the worker with the user's current session and revokes on logout
        from SaveNLoad.views.custom_decorators import get_current_user
        user = get_current_user(request)
        if hasattr(request, 'session'):
            if user:
                # User is logged in - associate worker with session
                request.session['client_id'] = client_id
                request.session.modified = True
            else:
                # User is logged out - clear client_id if it exists (revoke association)
                if 'client_id' in request.session:
                    request.session.pop('client_id', None)
                    request.session.modified = True
        
        print(f"Client worker registered: {client_id}")
        return json_response_success(
            message='Client worker registered successfully',
            data={'client_id': client_id}
        )
        
    except Exception as e:
        print(f"ERROR: Failed to register client: {e}")
        return json_response_error(str(e), status=500)


@csrf_exempt
@require_http_methods(["POST"])
def heartbeat(request):
    """Receive heartbeat from client worker and update user's session if logged in"""
    try:
        data, error_response = parse_json_body(request)
        if error_response:
            return error_response
        
        client_id = data.get('client_id', '').strip()
        
        worker, error_response = get_client_worker_by_id_or_error(client_id)
        if error_response:
            return error_response
        
        worker.last_heartbeat = timezone.now()
        worker.is_active = True
        worker.save()
        
        # If user is logged in, update their session with this client_id
        # If user is logged out, clear client_id from session (if it exists)
        # This associates the worker with the user's current session and revokes on logout
        from SaveNLoad.views.custom_decorators import get_current_user
        user = get_current_user(request)
        if hasattr(request, 'session'):
            if user:
                # User is logged in - associate worker with session
                request.session['client_id'] = client_id
                request.session.modified = True
            else:
                # User is logged out - clear client_id if it exists (revoke association)
                if 'client_id' in request.session:
                    request.session.pop('client_id', None)
                    request.session.modified = True
        
        return json_response_success()
        
    except Exception as e:
        print(f"ERROR: Failed to process heartbeat: {e}")
        return json_response_error(str(e), status=500)


@csrf_exempt
@require_http_methods(["POST"])
def unregister_client(request):
    """Unregister a client worker (called on shutdown)"""
    try:
        data, error_response = parse_json_body(request)
        if error_response:
            return error_response
        
        client_id = data.get('client_id', '').strip()
        
        worker, error_response = get_client_worker_by_id_or_error(client_id)
        if error_response:
            return error_response
        
        worker.is_active = False
        worker.save()
        print(f"Client worker unregistered: {client_id}")
        return json_response_success(message='Client worker unregistered')
        
    except Exception as e:
        print(f"ERROR: Failed to unregister client: {e}")
        return json_response_error(str(e), status=500)


@csrf_exempt
@require_http_methods(["GET"])
def check_connection(request):
    """Check if client worker is connected and update user's session if logged in"""
    # Get client_id from query parameter if provided
    client_id = request.GET.get('client_id', '').strip()
    
    if client_id:
        # Check specific client
        worker = ClientWorker.get_worker_by_id(client_id)
        is_connected = worker is not None and worker.is_online()
        
        # If user is logged in and worker is connected, store client_id in session
        # If user is logged out, clear client_id from session (if it exists)
        # This associates the worker with the user's current session and revokes on logout
        from SaveNLoad.views.custom_decorators import get_current_user
        user = get_current_user(request)
        if hasattr(request, 'session'):
            if user and is_connected:
                # User is logged in and worker is online - associate worker with session
                request.session['client_id'] = client_id
                request.session.modified = True
            elif not user and 'client_id' in request.session:
                # User is logged out - clear client_id (revoke association)
                request.session.pop('client_id', None)
                request.session.modified = True
        
        return JsonResponse({
            'connected': is_connected,
            'client_id': worker.client_id if worker and is_connected else None,
            'last_heartbeat': worker.last_heartbeat.isoformat() if worker and is_connected else None,
        })
    else:
        # No client_id provided - check if any worker is connected
        # If user is logged in, try to associate an active worker with their session
        from SaveNLoad.views.custom_decorators import get_current_user
        user = get_current_user(request)
        
        is_connected = ClientWorker.is_worker_connected()
        associated_worker = None
        
        # If user is logged in and worker is connected, try to associate one with session
        if user and is_connected and hasattr(request, 'session'):
            # First, check if there's already a client_id in session and if that worker is still online
            existing_client_id = request.session.get('client_id')
            if existing_client_id:
                existing_worker = ClientWorker.get_worker_by_id(existing_client_id)
                if existing_worker and existing_worker.is_online():
                    # Existing worker in session is still online - use it
                    associated_worker = existing_worker
                else:
                    # Existing worker is offline - clear it and find a new one
                    request.session.pop('client_id', None)
            
            # If no worker associated yet, find any active worker and associate it
            if not associated_worker:
                active_worker = ClientWorker.get_any_active_worker()
                if active_worker:
                    # Associate this worker with the user's session
                    request.session['client_id'] = active_worker.client_id
                    request.session.modified = True
                    associated_worker = active_worker
        
        # Build response
        response_data = {
            'connected': is_connected,
        }
        
        # Include client_id if we have an associated worker (for logged-in users)
        if associated_worker:
            response_data['client_id'] = associated_worker.client_id
            response_data['last_heartbeat'] = associated_worker.last_heartbeat.isoformat()
        
        return JsonResponse(response_data)


@csrf_exempt
@require_http_methods(["GET"])
def get_pending_operations(request, client_id):
    """Get pending operations for a client worker"""
    from SaveNLoad.models.operation_queue import OperationQueue, OperationStatus
    
    try:
        worker = ClientWorker.objects.get(client_id=client_id)
        
        # Handle stuck operations (in_progress for too long) - mark as failed
        from datetime import timedelta
        from django.db import transaction
        
        with transaction.atomic():
            # Find stuck operations assigned to this worker
            # Stuck = IN_PROGRESS for more than 30 minutes
            stuck_threshold = timezone.now() - timedelta(minutes=30)
            stuck_operations = OperationQueue.objects.select_for_update(skip_locked=True).filter(
                client_worker=worker,
                status=OperationStatus.IN_PROGRESS,
                started_at__lt=stuck_threshold
            )
            
            if stuck_operations.exists():
                # Mark stuck operations as failed
                stuck_ids = list(stuck_operations.values_list('id', flat=True))
                for op in stuck_operations:
                    op.mark_failed('Operation timed out after 30 minutes')
                print(f"WARNING: Marked {len(stuck_ids)} stuck operations as failed (operation timeout)")
        
        # Get pending operations assigned to this worker ONLY
        # Operations must be pre-assigned when created to prevent race conditions
        # Use select_for_update with skip_locked to prevent concurrent access
        with transaction.atomic():
            # Lock and get pending operations for this worker atomically
            operations = list(OperationQueue.objects.select_for_update(skip_locked=True).filter(
                client_worker=worker,
                status=OperationStatus.PENDING
            ).order_by('created_at'))
            
            # Mark operations as in_progress atomically
            if operations:
                operation_ids = [op.id for op in operations]
                OperationQueue.objects.filter(id__in=operation_ids).update(
                    status=OperationStatus.IN_PROGRESS,
                    started_at=timezone.now()
                )
                # Re-fetch to get updated objects with new status
                operations = list(OperationQueue.objects.filter(id__in=operation_ids))
        
        operations_list = []
        for op in operations:
            operations_list.append({
                'id': op.id,
                'type': op.operation_type,
                'game_id': op.game.id,
                'game_name': op.game.name,
                'local_save_path': op.local_save_path,
                'save_folder_number': op.save_folder_number,
                'remote_path': op.smb_path,  # Keep smb_path for backward compatibility, but use remote_path
                'smb_path': op.smb_path,  # Backward compatibility
                'username': op.user.username,
                'path_index': op.path_index,  # Add path_index to response
            })
        
        return JsonResponse({'operations': operations_list})
        
    except ClientWorker.DoesNotExist:
        return json_response_error('Client worker not found', status=404)


@csrf_exempt
@require_http_methods(["POST"])
def update_operation_progress(request, operation_id):
    """Update progress for an operation"""
    from SaveNLoad.models.operation_queue import OperationQueue
    
    try:
        data = json.loads(request.body or "{}")
        operation = OperationQueue.objects.get(pk=operation_id)
        
        # Update progress fields
        if 'current' in data:
            operation.progress_current = int(data.get('current', 0))
        if 'total' in data:
            operation.progress_total = int(data.get('total', 0))
        if 'message' in data:
            operation.progress_message = str(data.get('message', ''))[:200]  # Limit to 200 chars
        
        operation.save(update_fields=['progress_current', 'progress_total', 'progress_message'])
        
        return json_response_success()
        
    except OperationQueue.DoesNotExist:
        return json_response_error('Operation not found', status=404)
    except Exception as e:
        print(f"ERROR: Failed to update operation progress: {e}")
        return json_response_error(str(e), status=500)


@csrf_exempt
@require_http_methods(["POST"])
def complete_operation(request, operation_id):
    """Mark an operation as complete"""
    from SaveNLoad.models.operation_queue import OperationQueue
    from django.utils import timezone
    
    try:
        data = json.loads(request.body or "{}")
        operation = OperationQueue.objects.get(pk=operation_id)
        
        success = data.get('success', False)
        if success:
            operation.mark_completed(result_data=data)
            # Update game's last_played when save operation completes successfully
            from SaveNLoad.utils.operation_utils import is_operation_type, is_save_folder_operation
            if is_operation_type(operation, 'save'):
                operation.game.last_played = timezone.now()
                operation.game.save()
            # Delete save folder from database when DELETE operation completes successfully
            elif is_save_folder_operation(operation):
                from SaveNLoad.models.save_folder import SaveFolder
                try:
                    save_folder = SaveFolder.get_by_number(
                        operation.user,
                        operation.game,
                        operation.save_folder_number
                    )
                    if save_folder:
                        save_folder.delete()
                        print(f"Deleted save folder {operation.save_folder_number} from database after successful SMB deletion")
                except Exception as e:
                    print(f"WARNING: Failed to delete save folder from database after operation: {e}")
            
            # Check if game is pending deletion and all operations are complete
            from SaveNLoad.utils.operation_utils import (
                is_game_deletion_operation,
                get_pending_or_in_progress_operations,
                check_all_operations_succeeded
            )
            if operation.game.pending_deletion and is_game_deletion_operation(operation):
                # This is a game deletion operation - check if all operations for this game are complete
                remaining_operations = get_pending_or_in_progress_operations(
                    OperationQueue.objects.filter(game=operation.game)
                ).exclude(id=operation.id)
                
                if not remaining_operations.exists():
                    # All operations are complete - check if all succeeded
                    all_operations = OperationQueue.objects.filter(
                        game=operation.game,
                        operation_type='delete',
                        save_folder_number__isnull=True  # Game deletion operations
                    )
                    
                    all_succeeded = check_all_operations_succeeded(all_operations)
                    
                    if all_succeeded:
                        # All operations succeeded - delete the game
                        game_name = operation.game.name
                        game_id = operation.game.id
                        
                        # Delete banner file before deleting game
                        delete_game_banner_file(operation.game)
                        
                        operation.game.delete()  # This will CASCADE delete all SaveFolders and OperationQueue records
                        print(f"Game {game_id} ({game_name}) deleted from database after all FTP cleanup operations completed successfully")
                    else:
                        # Some operations failed - keep the game, clear pending_deletion flag
                        operation.game.pending_deletion = False
                        operation.game.save()
                        failed_count = all_operations.filter(status=OperationStatus.FAILED).count()
                        print(f"WARNING: Game {operation.game.id} ({operation.game.name}) deletion cancelled - {failed_count} FTP operation(s) failed")
        else:
            error_message = data.get('error', data.get('message', 'Operation failed'))
            
            # Transform error messages to be user-friendly
            from SaveNLoad.utils.string_utils import transform_path_error_message
            error_message = transform_path_error_message(error_message, operation.operation_type)
            
            operation.mark_failed(error_message)
            
            # Check if game is pending deletion and all operations are complete
            # Only check after all operations complete (per documentation: "After All Operations Complete")
            from SaveNLoad.utils.operation_utils import is_game_deletion_operation
            if operation.game.pending_deletion and is_game_deletion_operation(operation):
                # This is a game deletion operation - check if all operations for this game are complete
                from SaveNLoad.models.operation_queue import OperationStatus
                remaining_operations = OperationQueue.objects.filter(
                    game=operation.game,
                    status__in=[OperationStatus.PENDING, OperationStatus.IN_PROGRESS]
                ).exclude(id=operation.id)
                
                if not remaining_operations.exists():
                    # All operations are complete - check if all succeeded
                    all_operations = OperationQueue.objects.filter(
                        game=operation.game,
                        operation_type='delete',
                        save_folder_number__isnull=True  # Game deletion operations
                    )
                    
                    all_succeeded = all_operations.exclude(status=OperationStatus.COMPLETED).count() == 0
                    
                    if all_succeeded:
                        # All operations succeeded - delete the game
                        game_name = operation.game.name
                        game_id = operation.game.id
                        
                        # Delete banner file before deleting game
                        delete_game_banner_file(operation.game)
                        
                        operation.game.delete()  # This will CASCADE delete all SaveFolders and OperationQueue records
                        print(f"Game {game_id} ({game_name}) deleted from database after all FTP cleanup operations completed successfully")
                    else:
                        # Some operations failed - keep the game, clear pending_deletion flag
                        operation.game.pending_deletion = False
                        operation.game.save()
                        failed_count = all_operations.filter(status=OperationStatus.FAILED).count()
                        print(f"WARNING: Game {operation.game.id} ({operation.game.name}) deletion cancelled - {failed_count} FTP operation(s) failed")
            
            # Cleanup: If SAVE operation failed due to missing local path or empty saves, delete the save folder
            # This prevents orphaned save folders when user provides invalid path or empty saves
            from SaveNLoad.utils.operation_utils import is_operation_type
            if is_operation_type(operation, 'save') and operation.save_folder_number:
                error_lower = error_message.lower() if error_message else ''
                # Check if error is about local path not existing or empty saves
                path_errors = [
                    'does not exist',
                    'not found',
                    'local save path',
                    'local file not found',
                    'local path does not exist',
                    "don't have any save files",
                    "haven't played the game",
                    'empty',
                    'is empty',
                    'no files',
                    'no files were transferred',
                    'no files to save',
                    '0 bytes',
                    'nothing to save',
                    'contains no valid files',
                    'appears to be empty'
                ]
                if any(err in error_lower for err in path_errors):
                    from SaveNLoad.models.save_folder import SaveFolder
                    try:
                        save_folder = SaveFolder.get_by_number(
                            operation.user, 
                            operation.game, 
                            operation.save_folder_number
                        )
                        if save_folder:
                            # Check if save folder was created around the same time as the operation
                            # This ensures we only delete save folders created for this failed operation
                            from datetime import timedelta
                            time_threshold = operation.created_at - timedelta(minutes=1)
                            if save_folder.created_at >= time_threshold:
                                # Delete the save folder
                                save_folder.delete()
                                print(f"Deleted save folder {save_folder.folder_number} due to failed save operation (error: {error_message})")
                    except Exception as e:
                        print(f"WARNING: Failed to cleanup save folder after failed operation: {e}")
        
        return json_response_success()
        
    except OperationQueue.DoesNotExist:
        return json_response_error('Operation not found', status=404)
    except Exception as e:
        print(f"ERROR: Failed to complete operation: {e}")
        return json_response_error(str(e), status=500)



