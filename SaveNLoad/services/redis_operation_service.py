"""
Redis-based operation queue service
Handles operation creation, queuing, and status management
"""
from SaveNLoad.utils.redis_client import get_redis_client
from SaveNLoad.services.ws_worker_service import send_worker_message
from django.utils import timezone
import json
import uuid

# Operation status constants
class OperationStatus:
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    FAILED = 'failed'


def create_operation(operation_data, client_id):
    """
    Create a new operation and add it to worker's queue
    
    Args:
        operation_data: dict with operation details:
            - operation_type: str (save, load, delete, etc.)
            - user_id: int
            - game_id: int or None
            - local_save_path: str
            - save_folder_number: int or None
            - smb_path: str or None
            - path_index: int or None
        client_id: Worker identifier to assign operation to
    
    Returns:
        str: operation_id
    """
    redis_client = get_redis_client()
    
    # Generate unique operation ID
    operation_id = str(uuid.uuid4())
    
    # Prepare operation hash data
    operation_hash = {
        # Core identifiers and status.
        'id': operation_id,
        'type': operation_data['operation_type'],
        'status': OperationStatus.PENDING,
        'client_id': client_id,
        'user_id': str(operation_data['user_id']),
        'game_id': str(operation_data.get('game_id', '')) if operation_data.get('game_id') else '',
        'local_save_path': operation_data.get('local_save_path', ''),
        'save_folder_number': str(operation_data.get('save_folder_number', '')) if operation_data.get('save_folder_number') else '',
        'remote_ftp_path': operation_data.get('remote_ftp_path', '') or '',  # NEW: Pre-built FTP path from server
        # Timestamps and progress bookkeeping.
        'created_at': timezone.now().isoformat(),
        'started_at': '',
        'completed_at': '',
        'progress_current': '0',
        'progress_total': '0',
        'progress_message': '',
        'result_data': '',
        'error_message': ''
    }
    
    # Store operation in hash
    redis_client.hset(f'operation:{operation_id}', mapping=operation_hash)
    
    # Add to worker's operation list (left push for FIFO)
    redis_client.lpush(f'worker:{client_id}:operations', operation_id)
    
    # Notify worker via WebSocket
    # This pushes the full payload to the worker for immediate execution.
    send_worker_message(
        client_id,
        event_type='operation',
        payload=_build_operation_payload(operation_hash),
        correlation_id=operation_id
    )
    
    return operation_id


def get_pending_operations(client_id):
    """
    Get pending operations for a worker and mark them as in_progress
    
    Args:
        client_id: Worker identifier
    
    Returns:
        list of operation dicts
    """
    redis_client = get_redis_client()
    
    # Get all operation IDs from worker's list
    operation_ids = redis_client.lrange(f'worker:{client_id}:operations', 0, -1)
    
    pending_operations = []
    operation_ids_to_remove = []
    
    for operation_id in operation_ids:
        # Get operation hash
        operation_hash = redis_client.hgetall(f'operation:{operation_id}')
        
        if not operation_hash:
            # Operation doesn't exist, remove from list
            operation_ids_to_remove.append(operation_id)
            continue
        
        status = operation_hash.get('status', '')
        
        # Only return pending operations
        if status == OperationStatus.PENDING:
            # Mark as in_progress
            redis_client.hset(f'operation:{operation_id}', 'status', OperationStatus.IN_PROGRESS)
            redis_client.hset(f'operation:{operation_id}', 'started_at', timezone.now().isoformat())
            
            # Build operation dict
            operation_dict = {
                'id': operation_id,
                'type': operation_hash.get('type', ''),
                'local_save_path': operation_hash.get('local_save_path', ''),
                'save_folder_number': int(operation_hash['save_folder_number']) if operation_hash.get('save_folder_number') else None,
                'remote_ftp_path': operation_hash.get('remote_ftp_path', ''),  # Pre-built FTP path from server
            }
            
            
            pending_operations.append(operation_dict)
    
    # Remove invalid operation IDs from list
    for operation_id in operation_ids_to_remove:
        # Clean orphaned list entries.
        redis_client.lrem(f'worker:{client_id}:operations', 0, operation_id)
    
    return pending_operations


def get_pending_operations_for_worker(client_id):
    """
    Get pending operations for a worker without changing status.
    Intended for WS connect/reconnect to re-send pending work.
    
    Args:
        client_id: Worker identifier
    
    Returns:
        list of operation dicts
    """
    redis_client = get_redis_client()

    operation_ids = redis_client.lrange(f'worker:{client_id}:operations', 0, -1)
    pending_operations = []

    for operation_id in operation_ids:
        operation_hash = redis_client.hgetall(f'operation:{operation_id}')
        if not operation_hash:
            continue

        status = operation_hash.get('status', '')
        if status == OperationStatus.PENDING:
            # Only send pending operations on reconnect.
            pending_operations.append(_build_operation_payload(operation_hash))

    return pending_operations


def mark_operation_in_progress(operation_id):
    """
    Mark operation as in_progress
    
    Args:
        operation_id: Operation identifier
    """
    redis_client = get_redis_client()
    # Mark start time and status.
    redis_client.hset(f'operation:{operation_id}', 'status', OperationStatus.IN_PROGRESS)
    redis_client.hset(f'operation:{operation_id}', 'started_at', timezone.now().isoformat())


def complete_operation(operation_id, result_data=None):
    """
    Mark operation as completed and clean up
    
    Args:
        operation_id: Operation identifier
        result_data: Optional result data dict
    """
    redis_client = get_redis_client()
    
    # Update operation status
    redis_client.hset(f'operation:{operation_id}', 'status', OperationStatus.COMPLETED)
    redis_client.hset(f'operation:{operation_id}', 'completed_at', timezone.now().isoformat())
    
    if result_data:
        # Serialize result payload for later status checks.
        redis_client.hset(f'operation:{operation_id}', 'result_data', json.dumps(result_data))
    
    _remove_from_worker_queue(redis_client, operation_id)
    
    # Keep operation hash for a while (24 hours) for history, then delete
    # For now, we'll keep it indefinitely or until manually cleaned up


def fail_operation(operation_id, error_message):
    """
    Mark operation as failed and clean up
    
    Args:
        operation_id: Operation identifier
        error_message: Error message string
    """
    redis_client = get_redis_client()
    
    # Update operation status
    redis_client.hset(f'operation:{operation_id}', 'status', OperationStatus.FAILED)
    redis_client.hset(f'operation:{operation_id}', 'completed_at', timezone.now().isoformat())
    redis_client.hset(f'operation:{operation_id}', 'error_message', error_message)
    
    _remove_from_worker_queue(redis_client, operation_id)


def get_operation(operation_id):
    """
    Get operation details
    
    Args:
        operation_id: Operation identifier
    
    Returns:
        dict with operation details or None
    """
    redis_client = get_redis_client()
    operation_hash = redis_client.hgetall(f'operation:{operation_id}')
    
    if not operation_hash:
        return None
    
    return {
        'id': operation_hash.get('id'),
        'type': operation_hash.get('type'),
        'status': operation_hash.get('status'),
        'client_id': operation_hash.get('client_id'),
        'user_id': int(operation_hash['user_id']) if operation_hash.get('user_id') else None,
        'game_id': int(operation_hash['game_id']) if operation_hash.get('game_id') else None,
        'local_save_path': operation_hash.get('local_save_path', ''),
        'save_folder_number': int(operation_hash['save_folder_number']) if operation_hash.get('save_folder_number') else None,
        'smb_path': operation_hash.get('smb_path', ''),
        'path_index': int(operation_hash['path_index']) if operation_hash.get('path_index') else None,
        'created_at': operation_hash.get('created_at'),
        'started_at': operation_hash.get('started_at'),
        'completed_at': operation_hash.get('completed_at'),
        'progress_current': int(operation_hash.get('progress_current', 0)),
        'progress_total': int(operation_hash.get('progress_total', 0)),
        'progress_message': operation_hash.get('progress_message', ''),
        'result_data': json.loads(operation_hash['result_data']) if operation_hash.get('result_data') else None,
        'error_message': operation_hash.get('error_message', '')
    }


def update_operation_progress(operation_id, current=None, total=None, message=None):
    """
    Update operation progress
    
    Args:
        operation_id: Operation identifier
        current: Current progress count
        total: Total items
        message: Progress message
    """
    redis_client = get_redis_client()
    
    if current is not None:
        redis_client.hset(f'operation:{operation_id}', 'progress_current', str(current))
    if total is not None:
        redis_client.hset(f'operation:{operation_id}', 'progress_total', str(total))
    if message is not None:
        # Limit message size to keep Redis hash small.
        redis_client.hset(f'operation:{operation_id}', 'progress_message', str(message)[:200])


def _remove_from_worker_queue(redis_client, operation_id):
    """
    Remove an operation from a worker queue.
    
    Args:
        redis_client: Redis client instance
        operation_id: Operation identifier
    
    Returns:
        None
    """
    operation_hash = redis_client.hgetall(f'operation:{operation_id}')
    client_id = operation_hash.get('client_id') if operation_hash else None
    if client_id:
        # Fast-path removal using the stored client_id.
        redis_client.lrem(f'worker:{client_id}:operations', 0, operation_id)
        return

    # Fallback: search all worker queues if client_id is missing.
    worker_keys = redis_client.keys('worker:*:operations')
    for worker_key in worker_keys:
        redis_client.lrem(worker_key, 0, operation_id)


def _build_operation_payload(operation_hash):
    """
    Build the minimal operation payload sent to workers.
    
    Args:
        operation_hash: Operation hash dict from Redis
    
    Returns:
        dict with operation payload
    """
    # Payload format expected by the client worker.
    return {
        'id': operation_hash.get('id', ''),
        'type': operation_hash.get('type', ''),
        'local_save_path': operation_hash.get('local_save_path', ''),
        'save_folder_number': int(operation_hash['save_folder_number']) if operation_hash.get('save_folder_number') else None,
        'remote_ftp_path': operation_hash.get('remote_ftp_path', ''),
        'game_id': int(operation_hash.get('game_id')) if operation_hash.get('game_id') else None,
    }


def get_operations_by_game(game_id):
    """
    Get all operations for a game
    
    Args:
        game_id: Game ID
    
    Returns:
        list of operation dicts
    """
    redis_client = get_redis_client()
    
    # Get all operation keys
    operation_keys = redis_client.keys('operation:*')
    
    operations = []
    for key in operation_keys:
        operation_hash = redis_client.hgetall(key)
        if operation_hash.get('game_id') == str(game_id):
            # Resolve full operation record for consistent formatting.
            operations.append(get_operation(operation_hash.get('id')))
    
    return [op for op in operations if op]


def get_operations_by_user(user_id, game_id=None, operation_type=None):
    """
    Get all operations for a user, optionally filtered by game and type
    
    Args:
        user_id: User ID
        game_id: Optional game ID filter
        operation_type: Optional operation type filter
    
    Returns:
        list of operation dicts
    """
    redis_client = get_redis_client()
    
    # Get all operation keys
    operation_keys = redis_client.keys('operation:*')
    
    operations = []
    for key in operation_keys:
        operation_hash = redis_client.hgetall(key)
        if operation_hash.get('user_id') == str(user_id):
            # Apply filters
            if game_id and operation_hash.get('game_id') != str(game_id):
                continue
            if operation_type and operation_hash.get('type') != operation_type:
                continue
            # Resolve full operation record for consistent formatting.
            operations.append(get_operation(operation_hash.get('id')))
    
    return [op for op in operations if op]

