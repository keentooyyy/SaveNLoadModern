from urllib.parse import parse_qs
from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync
from SaveNLoad.services.redis_worker_service import (
    get_worker_info,
    register_worker,
    ping_worker,
    set_worker_ws_status,
    validate_ws_token,
)
from SaveNLoad.services.redis_operation_service import (
    mark_operation_in_progress,
    update_operation_progress,
    get_pending_operations_for_worker,
)
from SaveNLoad.services.operation_completion_service import process_operation_completion
from SaveNLoad.services.ws_worker_service import send_worker_message


class WorkerConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.client_id = self.scope['url_route']['kwargs'].get('client_id')
        token = self._get_token()

        if not self.client_id or not token or not validate_ws_token(self.client_id, token):
            self.close(code=4001)
            return

        worker_info = get_worker_info(self.client_id)
        if not worker_info:
            register_worker(self.client_id)

        async_to_sync(self.channel_layer.group_add)(
            f'worker.{self.client_id}',
            self.channel_name
        )
        self.accept()

        ping_worker(self.client_id)
        set_worker_ws_status(self.client_id, is_connected=True)

        pending_ops = get_pending_operations_for_worker(self.client_id)
        for operation in pending_ops:
            send_worker_message(
                self.client_id,
                event_type='operation',
                payload=operation,
                correlation_id=operation.get('id')
            )

    def disconnect(self, close_code):
        if not getattr(self, 'client_id', None):
            return

        async_to_sync(self.channel_layer.group_discard)(
            f'worker.{self.client_id}',
            self.channel_name
        )

        set_worker_ws_status(self.client_id, is_connected=False, mark_offline=True)

    def receive_json(self, content, **kwargs):
        message_type = content.get('type')
        payload = content.get('payload') or {}

        if message_type == 'heartbeat':
            ping_worker(self.client_id)
            return

        if message_type == 'operation_started':
            operation_id = payload.get('operation_id')
            if operation_id:
                mark_operation_in_progress(operation_id)
            return

        if message_type == 'progress':
            operation_id = payload.get('operation_id')
            if operation_id:
                current = payload.get('current')
                total = payload.get('total')
                message = payload.get('message')
                mark_operation_in_progress(operation_id)
                update_operation_progress(operation_id, current, total, message)
            return

        if message_type == 'complete':
            operation_id = payload.get('operation_id')
            if not operation_id:
                return
            process_operation_completion(operation_id, payload)
            return

    def worker_message(self, event):
        message = event.get('message') or {}
        self.send_json(message)

    def _get_token(self):
        query_string = self.scope.get('query_string', b'')
        try:
            parsed = parse_qs(query_string.decode('utf-8'))
        except Exception:
            return None
        token_list = parsed.get('token') or []
        return token_list[0] if token_list else None
