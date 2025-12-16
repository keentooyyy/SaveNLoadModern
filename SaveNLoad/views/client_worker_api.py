"""
API endpoints for client worker registration and communication
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from SaveNLoad.models.client_worker import ClientWorker
import json
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def register_client(request):
    """Register a client worker - client_id must be unique per PC"""
    try:
        data = json.loads(request.body or "{}")
        client_id = data.get('client_id', '').strip()
        
        if not client_id:
            return JsonResponse({'error': 'client_id is required'}, status=400)
        
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
        return JsonResponse({
            'success': True,
            'message': 'Client worker registered successfully',
            'client_id': client_id
        })
        
    except Exception as e:
        logger.error(f"Failed to register client: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def heartbeat(request):
    """Receive heartbeat from client worker"""
    try:
        data = json.loads(request.body or "{}")
        client_id = data.get('client_id', '').strip()
        
        if not client_id:
            return JsonResponse({'error': 'client_id is required'}, status=400)
        
        try:
            worker = ClientWorker.objects.get(client_id=client_id)
            worker.last_heartbeat = timezone.now()
            worker.is_active = True
            worker.save()
            return JsonResponse({'success': True})
        except ClientWorker.DoesNotExist:
            return JsonResponse({'error': 'Client not registered'}, status=404)
        
    except Exception as e:
        logger.error(f"Failed to process heartbeat: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def unregister_client(request):
    """Unregister a client worker (called on shutdown)"""
    try:
        data = json.loads(request.body or "{}")
        client_id = data.get('client_id', '').strip()
        
        if not client_id:
            return JsonResponse({'error': 'client_id is required'}, status=400)
        
        try:
            worker = ClientWorker.objects.get(client_id=client_id)
            worker.is_active = False
            worker.save()
            logger.info(f"Client worker unregistered: {client_id}")
            return JsonResponse({'success': True, 'message': 'Client worker unregistered'})
        except ClientWorker.DoesNotExist:
            return JsonResponse({'error': 'Client not registered'}, status=404)
        
    except Exception as e:
        logger.error(f"Failed to unregister client: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def check_connection(request):
    """Check if any client worker is connected"""
    is_connected = ClientWorker.is_worker_connected()
    worker = ClientWorker.get_any_active_worker()
    
    # Get all active workers for display
    all_workers = ClientWorker.get_active_workers()
    workers_list = [
        {
            'client_id': w.client_id,
            'last_heartbeat': w.last_heartbeat.isoformat(),
            'is_online': w.is_online()
        }
        for w in all_workers
    ]
    
    return JsonResponse({
        'connected': is_connected,
        'client_id': worker.client_id if worker and is_connected else None,
        'last_heartbeat': worker.last_heartbeat.isoformat() if worker and is_connected else None,
        'all_workers': workers_list,
        'total_workers': len(workers_list)
    })


@csrf_exempt
@require_http_methods(["GET"])
def get_pending_operations(request, client_id):
    """Get pending operations for a client worker"""
    from SaveNLoad.models.operation_queue import OperationQueue, OperationStatus
    
    try:
        worker = ClientWorker.objects.get(client_id=client_id)
        
        # Get pending operations assigned to this worker
        operations = OperationQueue.get_pending_operations_for_worker(worker)
        
        # Also get unassigned operations and assign them to this worker
        from SaveNLoad.models.operation_queue import OperationQueue
        unassigned = OperationQueue.objects.filter(
            status=OperationStatus.PENDING,
            client_worker__isnull=True
        ).order_by('created_at')
        
        # Assign unassigned operations to this worker
        for op in unassigned:
            op.assign_to_worker(worker)
            operations = list(operations) + [op]
        
        operations_list = []
        for op in operations:
            operations_list.append({
                'id': op.id,
                'type': op.operation_type,
                'game_id': op.game.id,
                'game_name': op.game.name,
                'local_save_path': op.local_save_path,
                'save_folder_number': op.save_folder_number,
                'username': op.user.username,
            })
        
        return JsonResponse({'operations': operations_list})
        
    except ClientWorker.DoesNotExist:
        return JsonResponse({'error': 'Client worker not found'}, status=404)


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
        else:
            error_message = data.get('error', data.get('message', 'Operation failed'))
            operation.mark_failed(error_message)
        
        return JsonResponse({'success': True})
        
    except OperationQueue.DoesNotExist:
        return JsonResponse({'error': 'Operation not found'}, status=404)
    except Exception as e:
        logger.error(f"Failed to complete operation: {e}")
        return JsonResponse({'error': str(e)}, status=500)

