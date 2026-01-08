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
from SaveNLoad.services.ws_worker_service import send_worker_message, worker_group_name


class WorkerConsumer(JsonWebsocketConsumer):
    """
    WebSocket consumer for client workers.
    Handles auth, presence, operations, and progress/completion updates.
    """
    def connect(self):
        """
        Handle WS connect and register worker into a group.

        Args:
            None

        Returns:
            None
        """
        self.client_id = self.scope['url_route']['kwargs'].get('client_id')
        token = self._get_token()
        print(f"WS connect attempt: client_id={self.client_id} has_token={bool(token)}")

        if not self.client_id:
            print("WS connect rejected: missing client_id")
            self.close(code=4001)
            return

        if not token:
            print(f"WS connect rejected: missing token for client_id={self.client_id}")
            self.close(code=4001)
            return

        if not validate_ws_token(self.client_id, token):
            print(f"WS connect rejected: invalid token for client_id={self.client_id}")
            self.close(code=4001)
            return

        worker_info = get_worker_info(self.client_id)
        if not worker_info:
            print(f"WS connect: registering worker client_id={self.client_id}")
            register_worker(self.client_id)
        else:
            print(f"WS connect: worker info found client_id={self.client_id} user_id={worker_info.get('user_id')}")

        async_to_sync(self.channel_layer.group_add)(
            worker_group_name(self.client_id),
            self.channel_name
        )
        self.accept()
        print(f"WS connected: client_id={self.client_id}")

        # Update heartbeat/presence and mark WS connected.
        print(f"WS presence update: client_id={self.client_id} ping+ws_status")
        ping_worker(self.client_id)
        set_worker_ws_status(self.client_id, is_connected=True)

        # Sync claim status on connect so the worker UI is accurate even if
        # the claim happened before the WS connection was established.
        worker_info = get_worker_info(self.client_id) or {}
        linked_user = worker_info.get('username') or ''
        claimed = bool(worker_info.get('user_id'))
        print(f"WS claim sync: client_id={self.client_id} claimed={claimed} linked_user={linked_user}")
        send_worker_message(
            self.client_id,
            event_type='claim_status',
            payload={
                'claimed': claimed,
                'linked_user': linked_user,
            }
        )

        # Re-send any pending operations so reconnects don't miss work.
        pending_ops = get_pending_operations_for_worker(self.client_id)
        if pending_ops:
            print(f"WS connect: sending {len(pending_ops)} pending ops to client_id={self.client_id}")
        for operation in pending_ops:
            # Push each pending operation as its own WS message.
            send_worker_message(
                self.client_id,
                event_type='operation',
                payload=operation,
                correlation_id=operation.get('id')
            )

    def disconnect(self, close_code):
        """
        Handle WS disconnect and mark worker offline.
        
        Args:
            close_code: WS close code
        
        Returns:
            None
        """
        if not getattr(self, 'client_id', None):
            return

        print(f"WS disconnected: client_id={self.client_id} code={close_code}")
        async_to_sync(self.channel_layer.group_discard)(
            worker_group_name(self.client_id),
            self.channel_name
        )

        # Immediate offline on disconnect (LAN assumption).
        print(f"WS presence update: client_id={self.client_id} ws_status=disconnected mark_offline=True")
        set_worker_ws_status(self.client_id, is_connected=False, mark_offline=True)

    def receive_json(self, content, **kwargs):
        """
        Handle incoming WS messages from the worker.
        
        Args:
            content: Parsed JSON payload
        
        Returns:
            None
        """
        message_type = content.get('type')
        payload = content.get('payload') or {}
        if not message_type:
            print(f"WS receive: missing type client_id={self.client_id}")
            return

        # Treat any inbound worker message as activity to refresh presence.
        ping_worker(self.client_id)

        if message_type == 'heartbeat':
            # Keep Redis heartbeat fresh during WS session.
            print(f"WS receive heartbeat: client_id={self.client_id}")
            return

        if message_type == 'operation_started':
            # Worker acknowledged operation start.
            operation_id = payload.get('operation_id')
            if operation_id:
                print(f"WS receive operation_started: client_id={self.client_id} op_id={operation_id}")
                mark_operation_in_progress(operation_id)
            return

        if message_type == 'progress':
            # Worker progress update for an in-flight operation.
            operation_id = payload.get('operation_id')
            if operation_id:
                current = payload.get('current')
                total = payload.get('total')
                message = payload.get('message')
                print(f"WS receive progress: client_id={self.client_id} op_id={operation_id} current={current} total={total}")
                # Ensure state is in-progress before updating progress counters.
                mark_operation_in_progress(operation_id)
                update_operation_progress(operation_id, current, total, message)
            return

        if message_type == 'complete':
            # Worker completion payload (success/failure + data).
            operation_id = payload.get('operation_id')
            if not operation_id:
                return
            print(f"WS receive complete: client_id={self.client_id} op_id={operation_id}")
            # Central handler updates Redis and any DB side effects.
            process_operation_completion(operation_id, payload)
            return

        print(f"WS receive: unknown type={message_type} client_id={self.client_id}")

    def worker_message(self, event):
        """
        Handler for group messages from the server to the worker.
        
        Args:
            event: Group event dict
        
        Returns:
            None
        """
        message = event.get('message') or {}
        message_type = message.get('type')
        print(f"WS send to worker: client_id={self.client_id} type={message_type}")
        self.send_json(message)

    def _get_token(self):
        """
        Extract WS auth token from the query string.

        Args:
            None

        Returns:
            Token string or None.
        """
        query_string = self.scope.get('query_string', b'')
        try:
            parsed = parse_qs(query_string.decode('utf-8'))
        except Exception:
            return None
        token_list = parsed.get('token') or []
        return token_list[0] if token_list else None
