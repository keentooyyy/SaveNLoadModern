import uuid
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def build_worker_message(event_type, payload=None, correlation_id=None):
    return {
        'type': event_type,
        'message_id': str(uuid.uuid4()),
        'timestamp': timezone.now().isoformat(),
        'correlation_id': correlation_id,
        'payload': payload or {},
    }


def send_worker_message(client_id, event_type, payload=None, correlation_id=None):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return False

    message = build_worker_message(
        event_type=event_type,
        payload=payload,
        correlation_id=correlation_id,
    )

    async_to_sync(channel_layer.group_send)(
        f'worker.{client_id}',
        {
            'type': 'worker.message',
            'message': message,
        }
    )
    return True
