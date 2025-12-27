"""
API endpoints for client worker registration and communication
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from SaveNLoad.models.client_worker import ClientWorker, WORKER_TIMEOUT_SECONDS
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
                'last_heartbeat': timezone.now()
            }
        )
        
        if not created:
            # Update existing worker
            worker.last_heartbeat = timezone.now()
            worker.save()
        
        print(f"Client worker registered: {client_id}")
        return json_response_success(
            message='Client worker registered successfully',
            data={
                'client_id': client_id,
                'linked_user': worker.user.username if worker.user else None
            }
        )
        
    except Exception as e:
        print(f"ERROR: Failed to register client: {e}")
        return json_response_error(str(e), status=500)


@csrf_exempt
@require_http_methods(["POST"])
def heartbeat(request):
    """Receive heartbeat from client worker and update status"""
    try:
        data, error_response = parse_json_body(request)
        if error_response:
            return error_response
        
        client_id = data.get('client_id', '').strip()
        
        worker, error_response = get_client_worker_by_id_or_error(client_id)
        if error_response:
            return error_response
        
        worker.last_heartbeat = timezone.now()
        worker.save()
        
        return json_response_success(data={
            'linked_user': worker.user.username if worker.user else None
        })
        
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
        
        # Worker is unregistered - no need to set is_active, is_online() will handle it
        print(f"Client worker unregistered: {client_id}")
        return json_response_success(message='Client worker unregistered')
        
    except Exception as e:
        print(f"ERROR: Failed to unregister client: {e}")
        return json_response_error(str(e), status=500)


@csrf_exempt
@require_http_methods(["GET"])
def check_connection(request):
    """Check if client worker is connected for current user"""
    from SaveNLoad.views.custom_decorators import get_current_user
    from SaveNLoad.models.client_worker import ClientWorker
    

    
    # Check for worker owned by this user - rely on relationship and is_online() check
    user = get_current_user(request)
    if not user:
        return JsonResponse({
            'connected': False,
            'client_id': None,
            'last_heartbeat': None,
        })
    
    # Get all workers owned by this user and filter by online status
    # No need for is_active check - is_online() is the source of truth
    user_workers = ClientWorker.objects.filter(user=user).order_by('-last_heartbeat')
    valid_workers = [w for w in user_workers if w.is_online(WORKER_TIMEOUT_SECONDS)]
    
    if not valid_workers:
        return JsonResponse({
            'connected': False,
            'client_id': None,
            'last_heartbeat': None,
            'message': 'No active devices found. Please ensure your client is running.'
        })
    
    # Smart Select:
    # If 1 active worker -> Use it automatically
    # If >1 active workers -> TODO: Implement selection (for now, use most recent)
    worker = valid_workers[0]
    
    return JsonResponse({
        'connected': True,
        'client_id': worker.client_id,
        'last_heartbeat': worker.last_heartbeat.isoformat(),
        'worker_count': len(valid_workers)
    })


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
            operation_data = {
                'id': op.id,
                'type': op.operation_type,
                'local_save_path': op.local_save_path,
                'save_folder_number': op.save_folder_number,
                'remote_path': op.smb_path,  # Keep smb_path for backward compatibility, but use remote_path
                'smb_path': op.smb_path,  # Backward compatibility
                'username': op.user.username,
                'path_index': op.path_index,  # Add path_index to response
            }
            
            # Add game info only if game exists (user deletion operations have game=None)
            if op.game:
                operation_data['game_id'] = op.game.id
                operation_data['game_name'] = op.game.name
            else:
                # User deletion operation - no game associated
                operation_data['game_id'] = None
                operation_data['game_name'] = None
            
            operations_list.append(operation_data)
        
        return JsonResponse({
            'operations': operations_list,
            'linked_user': worker.user.username if worker.user else None
        })
        
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



def _check_and_handle_game_deletion_completion(operation):
    """
    Check if game deletion is pending and all operations are complete.
    If so, either delete the game (if all succeeded) or cancel deletion (if any failed).
    """
    from SaveNLoad.models.operation_queue import OperationQueue, OperationStatus
    from SaveNLoad.utils.operation_utils import (
        is_game_deletion_operation,
        get_pending_or_in_progress_operations,
        check_all_operations_succeeded
    )
    
    if not (operation.game and operation.game.pending_deletion and is_game_deletion_operation(operation)):
        return

    # Check if all operations for this game are complete
    remaining_operations = get_pending_or_in_progress_operations(
        OperationQueue.objects.filter(game=operation.game)
    ).exclude(id=operation.id)
    
    if remaining_operations.exists():
        return

    # All operations are complete - check if all succeeded
    all_operations = OperationQueue.objects.filter(
        game=operation.game,
        operation_type='delete',
        save_folder_number__isnull=True  # Game deletion operations
    )
    
    # Check if any operation failed (including the current one if it failed)
    # We query the DB, so the current operation's status must be saved before calling this
    failed_ops_count = all_operations.filter(status=OperationStatus.FAILED).count()
    all_succeeded = failed_ops_count == 0
    
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
        print(f"WARNING: Game {operation.game.id} ({operation.game.name}) deletion cancelled - {failed_ops_count} FTP operation(s) failed")


def _check_and_handle_user_deletion_completion(operation):
    """
    Check if user deletion is pending and all operations are complete.
    If so, either delete the user (if all succeeded) or cancel deletion (if any failed).
    """
    from SaveNLoad.models.operation_queue import OperationQueue, OperationStatus
    from SaveNLoad.utils.operation_utils import (
        is_user_deletion_operation,
        get_pending_or_in_progress_operations,
    )
    
    # Refresh operation from database to get latest status
    try:
        operation.refresh_from_db()
        # Also refresh the user to get latest pending_deletion status
        operation.user.refresh_from_db()
    except (OperationQueue.DoesNotExist, AttributeError):
        return
    
    # Check if this is a user deletion operation
    if not (operation.user and hasattr(operation.user, 'pending_deletion') and operation.user.pending_deletion and is_user_deletion_operation(operation)):
        return

    print(f"DEBUG: Checking user deletion completion for user {operation.user.id} ({operation.user.username})")
    
    # Get all user deletion operations for this user (including the current one)
    # User deletion operations have game=None
    all_operations = OperationQueue.objects.filter(
        user=operation.user,
        game__isnull=True,  # User deletion operations
        operation_type='delete',
        save_folder_number__isnull=True
    )
    
    print(f"DEBUG: Found {all_operations.count()} user deletion operations for user {operation.user.id}")
    
    # Check if all operations are complete (including the current one)
    # The current operation should already be marked as COMPLETED when this function is called
    remaining_operations = get_pending_or_in_progress_operations(all_operations)
    
    if remaining_operations.exists():
        print(f"DEBUG: Still {remaining_operations.count()} pending/in-progress operations for user {operation.user.id}")
        # Log which operations are still pending
        for op in remaining_operations:
            print(f"DEBUG: Operation {op.id} status: {op.status}")
        return

    # All operations are complete - check if all succeeded
    failed_ops_count = all_operations.filter(status=OperationStatus.FAILED).count()
    completed_ops_count = all_operations.filter(status=OperationStatus.COMPLETED).count()
    total_ops_count = all_operations.count()
    
    # All operations must be completed (not failed, not pending, not in_progress)
    all_succeeded = (failed_ops_count == 0) and (completed_ops_count == total_ops_count) and (total_ops_count > 0)
    
    print(f"DEBUG: User deletion operations - Total: {total_ops_count}, Completed: {completed_ops_count}, Failed: {failed_ops_count}, All succeeded: {all_succeeded}")
    
    if all_succeeded:
        # All operations succeeded - delete the user
        username = operation.user.username
        user_id = operation.user.id
        
        # Add a small delay before deleting to give frontend time to poll operation status
        # This prevents the operation from being deleted (CASCADE) before the frontend can check it
        import time
        time.sleep(3)  # 3 second delay to allow frontend polling
        
        operation.user.delete()  # This will CASCADE delete all SaveFolders and OperationQueue records
        print(f"User {user_id} ({username}) deleted from database after FTP cleanup operation completed successfully")
    else:
        # Some operations failed - keep the user, clear pending_deletion flag
        operation.user.pending_deletion = False
        operation.user.save()
        print(f"WARNING: User {operation.user.id} ({operation.user.username}) deletion cancelled - {failed_ops_count} FTP operation(s) failed")


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
            # Refresh from DB to ensure we have the latest status
            operation.refresh_from_db()
            
            # Update game's last_played when save operation completes successfully
            from SaveNLoad.utils.operation_utils import is_operation_type, is_save_folder_operation
            if is_operation_type(operation, 'save') and operation.game:
                operation.game.last_played = timezone.now()
                operation.game.save()
            # Delete save folder from database when DELETE operation completes successfully
            elif is_save_folder_operation(operation) and operation.game:
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
            _check_and_handle_game_deletion_completion(operation)
            
            # Check if user is pending deletion and all operations are complete
            _check_and_handle_user_deletion_completion(operation)
        else:
            error_message = data.get('error', data.get('message', 'Operation failed'))
            
            # Transform error messages to be user-friendly
            from SaveNLoad.utils.string_utils import transform_path_error_message
            error_message = transform_path_error_message(error_message, operation.operation_type)
            
            operation.mark_failed(error_message)
            
            # Check if game is pending deletion and all operations are complete
            _check_and_handle_game_deletion_completion(operation)
            
            # Check if user is pending deletion and all operations are complete
            _check_and_handle_user_deletion_completion(operation)
            
            # Cleanup: If SAVE operation failed due to missing local path or empty saves, delete the save folder
            # This prevents orphaned save folders when user provides invalid path or empty saves
            # BUT: Only delete if ALL operations for this save folder have failed (for multiple save locations)
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
                    from SaveNLoad.models.operation_queue import OperationQueue, OperationStatus
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
                                # Check if there are other operations for this save folder that might succeed
                                # Only delete if ALL operations for this save folder have failed or completed
                                other_operations = OperationQueue.objects.filter(
                                    user=operation.user,
                                    game=operation.game,
                                    save_folder_number=operation.save_folder_number,
                                    operation_type=operation.operation_type
                                ).exclude(id=operation.id)
                                
                                # Check if any other operations are still pending or in progress
                                pending_or_in_progress = other_operations.filter(
                                    status__in=[OperationStatus.PENDING, OperationStatus.IN_PROGRESS]
                                ).exists()
                                
                                # Only delete if no other operations are pending/in-progress
                                # This allows other save locations to complete even if one fails
                                if not pending_or_in_progress:
                                    # Check if all other operations have also failed
                                    all_failed = not other_operations.filter(
                                        status=OperationStatus.COMPLETED
                                    ).exists()
                                    
                                    if all_failed:
                                        # All operations failed - safe to delete save folder
                                        save_folder.delete()
                                        print(f"Deleted save folder {save_folder.folder_number} due to failed save operation (error: {error_message})")
                                    else:
                                        # Some operations succeeded - keep the save folder
                                        print(f"Keeping save folder {save_folder.folder_number} - other operations succeeded")
                                else:
                                    # Other operations still pending - keep the save folder
                                    print(f"Keeping save folder {save_folder.folder_number} - other operations still pending")
                    except Exception as e:
                        print(f"WARNING: Failed to cleanup save folder after failed operation: {e}")
        
        return json_response_success()
        
    except OperationQueue.DoesNotExist:
        return json_response_error('Operation not found', status=404)
    except Exception as e:
        print(f"ERROR: Failed to complete operation: {e}")
        return json_response_error(str(e), status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_unpaired_workers(request):
    """Get list of active workers that are not paired with any user"""
    from SaveNLoad.views.custom_decorators import get_current_user
    from SaveNLoad.models.client_worker import ClientWorker

    
    user = get_current_user(request)
    if not user:
        return json_response_error('Authentication required', status=401)
    
    # Auto-unclaim offline workers to keep list accurate
    ClientWorker.unclaim_offline_workers(timeout_seconds=WORKER_TIMEOUT_SECONDS)
    
    # Get online workers that have no user assigned
    # Rely on is_online() check instead of cleanup
    active_workers = ClientWorker.get_active_workers(timeout_seconds=WORKER_TIMEOUT_SECONDS)
    unpaired_workers = [w for w in active_workers if w.user is None]
    
    return JsonResponse({
        'workers': [
            {
                'client_id': w.client_id,
                'last_heartbeat': w.last_heartbeat.isoformat(),
                # IP address was removed from plan, relying on hostname/client_id
                'hostname': w.client_id  # Assuming client_id contains hostname for now
            }
            for w in unpaired_workers
        ]
    })


@csrf_exempt
@require_http_methods(["POST"])
def claim_worker(request):
    """Claim a worker for the current user"""
    from SaveNLoad.views.custom_decorators import get_current_user
    
    try:
        user = get_current_user(request)
        if not user:
            return json_response_error('Authentication required', status=401)
            
        data, error_response = parse_json_body(request)
        if error_response:
            return error_response
            
        client_id = data.get('client_id', '').strip()
        if not client_id:
            return json_response_error('client_id is required', status=400)
            
        # Get the worker (must be active)
        # We don't use get_client_worker_by_id_or_error because we want to check if it's already claimed
        try:
            worker = ClientWorker.objects.get(client_id=client_id)
        except ClientWorker.DoesNotExist:
            return json_response_error('Worker not found', status=404)
            
        if not worker.is_online(WORKER_TIMEOUT_SECONDS):
            return json_response_error('Worker is offline', status=400)
            
        if worker.user and worker.user != user:
            return json_response_error('Worker is already claimed by another user', status=409)
            
        # Claim it
        worker.user = user
        worker.save()
        
        print(f"Worker {client_id} claimed by {user.username}")
        return json_response_success(message='Worker claimed successfully')
        
    except Exception as e:
        print(f"ERROR: Failed to claim worker: {e}")
        return json_response_error(str(e), status=500)


@csrf_exempt
@require_http_methods(["POST"])
def unclaim_worker(request):
    """Unclaim a worker (release ownership)"""
    from SaveNLoad.views.custom_decorators import get_current_user
    
    try:
        user = get_current_user(request)
        if not user:
            return json_response_error('Authentication required', status=401)
            
        data, error_response = parse_json_body(request)
        if error_response:
            return error_response
            
        client_id = data.get('client_id', '').strip()
        if not client_id:
            return json_response_error('client_id is required', status=400)
            
        try:
            worker = ClientWorker.objects.get(client_id=client_id, user=user)
        except ClientWorker.DoesNotExist:
            return json_response_error('Worker not found or not owned by you', status=404)
            
        # Release it
        worker.user = None
        worker.save()
        
        print(f"Worker {client_id} unclaimed by {user.username}")
        return json_response_success(message='Worker unclaimed successfully')
        
    except Exception as e:
        print(f"ERROR: Failed to unclaim worker: {e}")
        return json_response_error(str(e), status=500)



