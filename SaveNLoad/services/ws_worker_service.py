import re
import uuid
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def build_worker_message(event_type, payload=None, correlation_id=None):
    """
    Build a standardized WS payload envelope sent to a worker.
    
    Args:
        event_type: Event type string
        payload: Optional payload dict
        correlation_id: Optional correlation ID string
    
    Returns:
        dict with message envelope
    """
    return {
        'type': event_type,
        'message_id': str(uuid.uuid4()),
        'timestamp': timezone.now().isoformat(),
        'correlation_id': correlation_id,
        'payload': payload or {},  # Always send a dict for predictable client parsing.
    }


def worker_group_name(client_id):
    """
    Normalize client_id into a Channels-safe group name.
    Channels group names allow only ASCII alphanumerics, hyphens, underscores, and periods.
    
    Args:
        client_id: Worker identifier
    
    Returns:
        str: Sanitized group name
    """
    # Replace invalid characters (e.g., colons in MAC addresses).
    safe_id = re.sub(r'[^A-Za-z0-9_.-]', '_', client_id or '')
    if not safe_id:
        safe_id = 'unknown'
    # Keep group names under Channels length limit.
    return f'worker.{safe_id}'[:96]


def send_worker_message(client_id, event_type, payload=None, correlation_id=None):
    """
    Send a WS message to a worker group (no-op if channel layer is unavailable).
    Returns: True if enqueued, False otherwise.
    
    Args:
        client_id: Worker identifier
        event_type: Event type string
        payload: Optional payload dict
        correlation_id: Optional correlation ID string
    
    Returns:
        bool: True if enqueued, False otherwise
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return False

    # Build the envelope once so all consumers see a consistent message format.
    message = build_worker_message(
        event_type=event_type,
        payload=payload,
        correlation_id=correlation_id,
    )

    async_to_sync(channel_layer.group_send)(
        worker_group_name(client_id),
        {
            'type': 'worker.message',
            'message': message,
        }
    )
    return True


def ui_workers_group_name():
    """
    Group name for UI clients that want worker list updates.
    
    Returns:
        str: Group name
    """
    return 'ui.workers'


def send_ui_workers_update(workers):
    """
    Broadcast worker list updates to UI listeners.
    
    Args:
        workers: List of worker dicts
    
    Returns:
        bool: True if enqueued, False otherwise
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return False

    message = build_worker_message(
        event_type='workers_update',
        payload={'workers': workers}
    )

    async_to_sync(channel_layer.group_send)(
        ui_workers_group_name(),
        {
            'type': 'ui.message',
            'message': message,
        }
    )
    return True


def ui_user_group_name(user_id):
    """
    Group name for UI clients scoped to a single user.
    
    Args:
        user_id: User identifier
    
    Returns:
        str: Group name
    """
    safe_id = str(user_id) if user_id is not None else 'unknown'
    return f'ui.user.{safe_id}'


def send_ui_user_worker_status(user_id, connected):
    """
    Broadcast worker availability status to a specific user's UI clients.
    
    Args:
        user_id: User identifier
        connected: True if any worker is online for the user
    
    Returns:
        bool: True if enqueued, False otherwise
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return False

    message = build_worker_message(
        event_type='worker_status',
        payload={'connected': bool(connected)}
    )

    async_to_sync(channel_layer.group_send)(
        ui_user_group_name(user_id),
        {
            'type': 'ui.user.message',
            'message': message,
        }
    )
    return True
