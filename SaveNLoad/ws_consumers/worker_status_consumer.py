from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync
from SaveNLoad.services.ws_worker_service import ui_user_group_name
from SaveNLoad.ws_consumers.ws_auth import get_ws_user


class UserWorkerStatusConsumer(JsonWebsocketConsumer):
    """
    WebSocket consumer for user-scoped worker availability status.
    """
    def connect(self):
        """
        Accept authenticated UI clients and send initial worker status.

        Args:
            None

        Returns:
            None
        """
        user = self._get_session_user()
        if not user:
            self.close(code=4001)
            return

        async_to_sync(self.channel_layer.group_add)(
            ui_user_group_name(user.id),
            self.channel_name
        )
        self.accept()
        # Send current status so UI can react immediately.
        self._send_status(user.id)

    def disconnect(self, close_code):
        """
        Remove UI client from the user status group.

        Args:
            close_code: WebSocket close code

        Returns:
            None
        """
        user = self._get_session_user()
        if not user:
            return
        async_to_sync(self.channel_layer.group_discard)(
            ui_user_group_name(user.id),
            self.channel_name
        )

    def ui_user_message(self, event):
        """
        Forward worker status updates to the UI client.

        Args:
            event: Group event dict

        Returns:
            None
        """
        message = event.get('message') or {}
        self.send_json(message)

    def _send_status(self, user_id):
        """
        Send current worker availability to the UI client.

        Args:
            user_id: User identifier

        Returns:
            None
        """
        from SaveNLoad.services.redis_worker_service import has_online_worker
        self.send_json({
            'type': 'worker_status',
            'payload': {'connected': has_online_worker(user_id)}
        })

    def _get_session_user(self):
        """
        Resolve the current user from the session for custom auth.

        Args:
            None

        Returns:
            SimpleUsers or None
        """
        return get_ws_user(self.scope)
