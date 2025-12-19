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
    json_response_success
)
import json
import logging

logger = logging.getLogger(__name__)


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
        
        logger.info(f"Client worker registered: {client_id}")
        return json_response_success(
            message='Client worker registered successfully',
            data={'client_id': client_id}
        )
        
    except Exception as e:
        logger.error(f"Failed to register client: {e}")
        return json_response_error(str(e), status=500)


@csrf_exempt
@require_http_methods(["POST"])
def heartbeat(request):
    """Receive heartbeat from client worker"""
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
        return json_response_success()
        
    except Exception as e:
        logger.error(f"Failed to process heartbeat: {e}")
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
        logger.info(f"Client worker unregistered: {client_id}")
        return json_response_success(message='Client worker unregistered')
        
    except Exception as e:
        logger.error(f"Failed to unregister client: {e}")
        return json_response_error(str(e), status=500)


@csrf_exempt
@require_http_methods(["GET"])
def check_connection(request):
    """Check if client worker is connected - only returns info for the requesting client"""
    # Get client_id from query parameter if provided
    client_id = request.GET.get('client_id', '').strip()
    
    if client_id:
        # Check specific client
        worker = ClientWorker.get_worker_by_id(client_id)
        is_connected = worker is not None and worker.is_online()
        
        return JsonResponse({
            'connected': is_connected,
            'client_id': worker.client_id if worker and is_connected else None,
            'last_heartbeat': worker.last_heartbeat.isoformat() if worker and is_connected else None,
        })
    else:
        # No client_id provided - just check if any worker is connected (for backward compatibility)
        # Don't expose other clients' information
        is_connected = ClientWorker.is_worker_connected()
        
        return JsonResponse({
            'connected': is_connected,
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
                logger.warning(f"Marked {len(stuck_ids)} stuck operations as failed (operation timeout)")
        
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
        logger.error(f"Failed to update operation progress: {e}")
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
            if operation.operation_type == 'save':
                operation.game.last_played = timezone.now()
                operation.game.save()
            # Delete save folder from database when DELETE operation completes successfully
            elif operation.operation_type == 'delete' and operation.save_folder_number:
                from SaveNLoad.models.save_folder import SaveFolder
                try:
                    save_folder = SaveFolder.get_by_number(
                        operation.user,
                        operation.game,
                        operation.save_folder_number
                    )
                    if save_folder:
                        save_folder.delete()
                        logger.info(f"Deleted save folder {operation.save_folder_number} from database after successful SMB deletion")
                except Exception as e:
                    logger.warning(f"Failed to delete save folder from database after operation: {e}")
        else:
            error_message = data.get('error', data.get('message', 'Operation failed'))
            
            # Transform error messages to be user-friendly
            error_lower = error_message.lower() if error_message else ''
            if 'local save path does not exist' in error_lower or 'local file not found' in error_lower:
                if operation.operation_type == 'save':
                    error_message = 'Oops! You don\'t have any save files to save. Maybe you haven\'t played the game yet, or the save location is incorrect.'
                elif operation.operation_type == 'load':
                    error_message = 'Oops! You don\'t have any save files to load. Maybe you haven\'t saved this game yet.'
            
            operation.mark_failed(error_message)
            
            # Cleanup: If SAVE operation failed due to missing local path or empty saves, delete the save folder
            # This prevents orphaned save folders when user provides invalid path or empty saves
            if operation.operation_type == 'save' and operation.save_folder_number:
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
                                logger.info(f"Deleted save folder {save_folder.folder_number} due to failed save operation (error: {error_message})")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup save folder after failed operation: {e}")
        
        return json_response_success()
        
    except OperationQueue.DoesNotExist:
        return json_response_error('Operation not found', status=404)
    except Exception as e:
        logger.error(f"Failed to complete operation: {e}")
        return json_response_error(str(e), status=500)



