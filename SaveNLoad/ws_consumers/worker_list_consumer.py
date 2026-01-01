from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync
from SaveNLoad.services.ws_worker_service import ui_workers_group_name


class WorkerListConsumer(JsonWebsocketConsumer):
    """
    WebSocket consumer for UI clients that need real-time worker updates.
    """
    def connect(self):
        """
        Accept authenticated UI clients and send initial worker snapshot.

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
            ui_workers_group_name(),
            self.channel_name
        )
        self.accept()
        self._send_snapshot()

    def disconnect(self, close_code):
        """
        Remove UI client from the worker updates group.

        Args:
            close_code: WebSocket close code

        Returns:
            None
        """
        async_to_sync(self.channel_layer.group_discard)(
            ui_workers_group_name(),
            self.channel_name
        )

    def ui_message(self, event):
        """
        Forward worker update messages to the UI client.

        Args:
            event: Group event dict

        Returns:
            None
        """
        message = event.get('message') or {}
        self.send_json(message)

    def _send_snapshot(self):
        """
        Send a full worker list snapshot to the UI client.

        Args:
            None

        Returns:
            None
        """
        from SaveNLoad.services.redis_worker_service import get_workers_snapshot
        workers = get_workers_snapshot()
        self.send_json({
            'type': 'workers_update',
            'payload': {'workers': workers}
        })

    def _get_session_user(self):
        """
        Resolve the current user from the session for custom auth.

        Args:
            None

        Returns:
            SimpleUsers or None
        """
        session = self.scope.get('session')
        if not session:
            return None
        user_id = session.get('user_id')
        if not user_id:
            return None
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return None
        if user_id <= 0:
            return None
        from SaveNLoad.models import SimpleUsers
        try:
            return SimpleUsers.objects.get(id=user_id)
        except SimpleUsers.DoesNotExist:
            return None
