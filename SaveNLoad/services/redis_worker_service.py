"""
Redis-based worker management service
Handles worker registration, heartbeat, claiming, and online status
"""
from SaveNLoad.utils.redis_client import get_redis_client
from SaveNLoad.services.ws_worker_service import (
    send_worker_message,
    send_ui_workers_update,
    send_ui_user_worker_status,
)
from django.utils import timezone
import secrets

# Worker heartbeat TTL (10 seconds - worker pings every 5s, so this allows 1 missed ping)
WORKER_HEARTBEAT_TTL = 10


def register_worker(client_id, user_id=None):
    """
    Register a worker with Redis
    Creates heartbeat key and info hash
    
    Args:
        client_id: Unique worker identifier
        user_id: Optional user ID if worker is already claimed
    
    Returns:
        dict with worker info
    """
    redis_client = get_redis_client()
    
    # Set heartbeat key with TTL
    redis_client.setex(f'worker:{client_id}', WORKER_HEARTBEAT_TTL, '1')
    
    existing_info = redis_client.hgetall(f'worker:{client_id}:info') or {}

    # Create or update worker info hash
    worker_info = {
        # Preserve existing ownership unless a new user_id is provided.
        'user_id': str(user_id) if user_id else existing_info.get('user_id', ''),
        'created_at': existing_info.get('created_at', timezone.now().isoformat()),
        'last_ping': timezone.now().isoformat(),
        # Track WS status/tokens for realtime comms.
        'ws_connected': existing_info.get('ws_connected', '0'),
        'ws_token': existing_info.get('ws_token', ''),
    }
    redis_client.hset(f'worker:{client_id}:info', mapping=worker_info)
    
    # If user_id provided, add to user's worker set
    if user_id:
        redis_client.sadd(f'user:{user_id}:workers', client_id)
    
    worker_data = {
        'client_id': client_id,
        'user_id': user_id,
        'created_at': worker_info['created_at']
    }
    _notify_ui_workers_update()
    _notify_ui_user_worker_status(user_id)
    return worker_data


def ping_worker(client_id):
    """
    Update worker heartbeat (refresh TTL)
    
    Args:
        client_id: Worker identifier
    
    Returns:
        dict with linked_user or None
    """
    redis_client = get_redis_client()
    
    # Refresh heartbeat TTL
    redis_client.setex(f'worker:{client_id}', WORKER_HEARTBEAT_TTL, '1')
    
    # Update last_ping in info hash
    redis_client.hset(f'worker:{client_id}:info', 'last_ping', timezone.now().isoformat())
    
    # Get linked user
    user_id = redis_client.hget(f'worker:{client_id}:info', 'user_id')
    
    if user_id:
        from SaveNLoad.models import SimpleUsers
        try:
            user = SimpleUsers.objects.get(pk=int(user_id))
            return {'linked_user': user.username}
        except SimpleUsers.DoesNotExist:
            # User doesn't exist, clear the user_id
            redis_client.hset(f'worker:{client_id}:info', 'user_id', '')
            redis_client.hset(f'worker:{client_id}:info', 'username', '')
            redis_client.srem(f'user:{user_id}:workers', client_id)
            try:
                # Legacy pub/sub cleanup; safe to ignore errors.
                redis_client.publish(f'worker:{client_id}:notify', 'claim_status_changed')
            except Exception:
                pass
            return {'linked_user': None}
    
    return {'linked_user': None}


def issue_ws_token(client_id):
    """
    Issue or rotate a WebSocket auth token for the worker.
    
    Args:
        client_id: Worker identifier
    
    Returns:
        str: Token string
    """
    redis_client = get_redis_client()
    token = secrets.token_urlsafe(32)
    # Store token and timestamp in the worker info hash.
    redis_client.hset(
        f'worker:{client_id}:info',
        mapping={
            'ws_token': token,
            'ws_token_created_at': timezone.now().isoformat()
        }
    )
    return token


def validate_ws_token(client_id, token):
    """
    Validate a WebSocket auth token for a worker.
    
    Args:
        client_id: Worker identifier
        token: Token string
    
    Returns:
        bool: True if valid, False otherwise
    """
    redis_client = get_redis_client()
    stored = redis_client.hget(f'worker:{client_id}:info', 'ws_token')
    return bool(stored) and stored == token


def set_worker_ws_status(client_id, is_connected, mark_offline=False):
    """
    Update WebSocket connection status and optionally mark the worker offline immediately.
    
    Args:
        client_id: Worker identifier
        is_connected: True if WS connected, False otherwise
        mark_offline: If True, delete heartbeat key immediately
    
    Returns:
        None
    """
    redis_client = get_redis_client()
    now = timezone.now().isoformat()

    mapping = {
        'ws_connected': '1' if is_connected else '0',
    }
    if is_connected:
        # Treat WS connect as online and refresh TTL.
        mapping['last_ws_connect'] = now
        redis_client.setex(f'worker:{client_id}', WORKER_HEARTBEAT_TTL, '1')
    else:
        # On disconnect, optionally mark offline immediately.
        mapping['last_ws_disconnect'] = now
        if mark_offline:
            redis_client.delete(f'worker:{client_id}')

    redis_client.hset(f'worker:{client_id}:info', mapping=mapping)
    _notify_ui_workers_update()
    user_id = redis_client.hget(f'worker:{client_id}:info', 'user_id')
    # Notify user-scoped listeners about availability changes.
    _notify_ui_user_worker_status(user_id)


def get_worker_info(client_id):
    """
    Get worker information
    
    Args:
        client_id: Worker identifier
    
    Returns:
        dict with worker info or None if not found
    """
    redis_client = get_redis_client()
    
    # Check if worker exists (heartbeat key)
    if not redis_client.exists(f'worker:{client_id}'):
        return None
    
    # Get info hash
    info = redis_client.hgetall(f'worker:{client_id}:info')
    
    if not info:
        return None
    
    return {
        'client_id': client_id,
        'user_id': int(info['user_id']) if info.get('user_id') else None,
        'created_at': info.get('created_at'),
        'last_ping': info.get('last_ping'),
        'ws_connected': info.get('ws_connected') == '1',
        'username': info.get('username')
    }


def get_worker_claim_data(client_id):
    """
    Get worker claim data without requiring the heartbeat key.

    Args:
        client_id: Worker identifier

    Returns:
        (user_id, username) tuple; user_id is int or None
    """
    redis_client = get_redis_client()
    info = redis_client.hgetall(f'worker:{client_id}:info') or {}

    user_id = info.get('user_id')
    username = info.get('username')

    if isinstance(user_id, bytes):
        user_id = user_id.decode('utf-8')
    if isinstance(username, bytes):
        username = username.decode('utf-8')

    if user_id:
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            user_id = None
    else:
        user_id = None

    return user_id, username


def claim_worker(client_id, user_id, username=None):
    """
    Claim a worker for a user
    
    Args:
        client_id: Worker identifier
        user_id: User ID to claim the worker
        username: Optional username to store in Redis (for client worker display)
    
    Returns:
        True if successful, False if worker not found or already claimed by another user
    """
    redis_client = get_redis_client()
    
    # Check if worker exists and is online
    if not is_worker_online(client_id):
        return False
    
    # Get current user_id
    current_user_id = redis_client.hget(f'worker:{client_id}:info', 'user_id')
    
    # If already claimed by another user, return False
    if current_user_id and int(current_user_id) != user_id:
        return False
    
    # Claim the worker - store both user_id and username
    redis_client.hset(f'worker:{client_id}:info', 'user_id', str(user_id))
    if username:
        redis_client.hset(f'worker:{client_id}:info', 'username', username)
    redis_client.sadd(f'user:{user_id}:workers', client_id)
    
    # Notify worker about claim status change.
    send_worker_message(
        client_id,
        event_type='claim_status',
        payload={
            'claimed': True,
            'linked_user': username or ''
        }
    )
    _notify_ui_workers_update()
    _notify_ui_user_worker_status(user_id)
    
    return True


def unclaim_worker(client_id):
    """
    Unclaim a worker (remove user assignment)
    
    Args:
        client_id: Worker identifier
    
    Returns:
        True if successful, False if worker not found
    """
    redis_client = get_redis_client()
    
    # Get current user_id
    user_id = redis_client.hget(f'worker:{client_id}:info', 'user_id')
    
    if not user_id:
        return True  # Already unclaimed
    
    # Remove from user's worker set
    redis_client.srem(f'user:{user_id}:workers', client_id)
    
    # Clear user_id and username from worker info
    redis_client.hset(f'worker:{client_id}:info', 'user_id', '')
    redis_client.hset(f'worker:{client_id}:info', 'username', '')
    
    # Notify worker about claim status change.
    send_worker_message(
        client_id,
        event_type='claim_status',
        payload={
            'claimed': False,
            'linked_user': ''
        }
    )
    _notify_ui_workers_update()
    _notify_ui_user_worker_status(user_id)
    
    return True


def get_user_workers(user_id):
    """
    Get all workers for a user
    
    Args:
        user_id: User ID
    
    Returns:
        list of client_ids
    """
    redis_client = get_redis_client()
    
    # Get all workers from user's set
    worker_ids = redis_client.smembers(f'user:{user_id}:workers')
    
    # Filter to only online workers
    online_workers = []
    for worker_id in worker_ids:
        if is_worker_online(worker_id):
            online_workers.append(worker_id)
        else:
            # Worker is offline - auto-unclaim it
            # Remove from user's set
            unclaim_worker(worker_id)
            print(f"Auto-unclaimed offline worker {worker_id} for user {user_id}")
    
    return list(online_workers)


def is_worker_online(client_id):
    """
    Check if worker is online (heartbeat key exists)
    
    Args:
        client_id: Worker identifier
    
    Returns:
        bool
    """
    redis_client = get_redis_client()
    return redis_client.exists(f'worker:{client_id}') > 0


def get_online_workers():
    """
    Get all online workers
    
    Returns:
        list of client_ids
    """
    redis_client = get_redis_client()
    
    # Get all worker keys
    worker_keys = redis_client.keys('worker:*')
    
    # Filter out sub-keys (info, operations, notify) - only keep exact worker heartbeat keys
    # Sub-keys have pattern: 'worker:{client_id}:info', 'worker:{client_id}:operations', etc.
    # Heartbeat keys have pattern: 'worker:{client_id}' (but client_id can contain colons)
    online_workers = []
    seen_client_ids = set()
    
    # Known sub-key suffixes
    sub_key_suffixes = [':info', ':operations', ':notify']
    
    for key in worker_keys:
        # Check if this is a sub-key by checking if it ends with known suffixes
        is_sub_key = any(key.endswith(suffix) for suffix in sub_key_suffixes)
        if is_sub_key:
            continue
        
        # Remove 'worker:' prefix to get client_id
        # Note: client_id can contain colons (e.g., MAC address format)
        client_id = key.replace('worker:', '', 1)
        
        # This is a valid worker heartbeat key
        if client_id and client_id not in seen_client_ids:
            # Verify it exists (is online) - heartbeat keys are simple string keys
            if redis_client.exists(key) > 0:
                # Double-check it's not a hash/list by checking the type
                key_type = redis_client.type(key).decode('utf-8') if isinstance(redis_client.type(key), bytes) else redis_client.type(key)
                if key_type == 'string':  # Heartbeat keys are strings
                    online_workers.append(client_id)
                    seen_client_ids.add(client_id)
    
    return online_workers


def has_online_worker(user_id):
    """
    Check if a user has any online workers without mutating claim state.
    
    Args:
        user_id: User identifier
    
    Returns:
        bool
    """
    if not user_id:
        return False
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return False
    
    redis_client = get_redis_client()
    worker_ids = redis_client.smembers(f'user:{user_id}:workers')
    for worker_id in worker_ids:
        if is_worker_online(worker_id):
            return True
    return False


def get_unclaimed_workers():
    """
    Get all online workers that are not claimed by any user
    
    Returns:
        list of client_ids
    """
    redis_client = get_redis_client()
    
    online_workers = get_online_workers()
    unclaimed = []
    
    for client_id in online_workers:
        user_id = redis_client.hget(f'worker:{client_id}:info', 'user_id')
        if not user_id or user_id == '':
            unclaimed.append(client_id)
        else:
            # Worker is online but claimed - verify it's still in user's set
            # If not, it means the user's set was cleaned up but worker info wasn't
            # This handles edge cases where cleanup might have been partial
            if not redis_client.sismember(f'user:{user_id}:workers', client_id):
                # Orphaned claim - clean it up
                unclaim_worker(client_id)
                unclaimed.append(client_id)
                print(f"Auto-unclaimed orphaned worker {client_id}")
    
    return unclaimed


def get_workers_snapshot():
    """
    Get a snapshot of all online workers with claim status.
    
    Returns:
        list of worker dicts
    """
    from SaveNLoad.models import SimpleUsers
    
    workers_list = []
    for client_id in sorted(get_online_workers()):
        worker_info = get_worker_info(client_id)
        user_id = worker_info.get('user_id') if worker_info else None
        linked_username = worker_info.get('username') if worker_info else None
        if user_id and not linked_username:
            try:
                linked_user = SimpleUsers.objects.get(pk=user_id)
                linked_username = linked_user.username
            except SimpleUsers.DoesNotExist:
                linked_username = None
        
        workers_list.append({
            'client_id': client_id,
            'last_ping_response': worker_info.get('last_ping') if worker_info else None,
            'hostname': client_id,
            'linked_user': linked_username,
            'claimed': user_id is not None
        })
    
    return workers_list


def _notify_ui_workers_update():
    """
    Best-effort broadcast of worker list updates to UI listeners.

    Args:
        None

    Returns:
        None
    """
    try:
        send_ui_workers_update(get_workers_snapshot())
    except Exception as e:
        print(f"UI workers update failed: {e}")


def _notify_ui_user_worker_status(user_id):
    """
    Best-effort broadcast of user worker availability to UI listeners.

    Args:
        user_id: User identifier

    Returns:
        None
    """
    if not user_id:
        return
    try:
        send_ui_user_worker_status(user_id, has_online_worker(user_id))
    except Exception as e:
        print(f"UI user status update failed: {e}")

