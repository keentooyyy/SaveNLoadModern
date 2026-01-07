from django.core.management.base import BaseCommand
from django.utils import timezone

from SaveNLoad.models import SimpleUsers
from SaveNLoad.models.operation_constants import OperationType
from SaveNLoad.services.redis_operation_service import create_operation
from SaveNLoad.utils.redis_client import get_redis_client


class Command(BaseCommand):
    help = "Delete expired guest users and enqueue storage cleanup."

    def handle(self, *args, **options):
        now = timezone.now()
        expired_guests = SimpleUsers.objects.filter(
            is_guest=True,
            guest_expires_at__isnull=False,
            guest_expires_at__lte=now
        ).exclude(pending_deletion=True)

        if not expired_guests.exists():
            self.stdout.write("No expired guests found.")
            return

        redis_client = get_redis_client()
        worker_id = self._get_any_worker(redis_client)

        if not worker_id:
            self.stdout.write("No online worker found. Skipping cleanup.")
            return

        for guest in expired_guests:
            namespace = guest.guest_namespace or guest.username
            create_operation(
                {
                    'operation_type': OperationType.DELETE,
                    'operation_group': 'user_delete',
                    'user_id': guest.id,
                    'game_id': None,
                    'local_save_path': '',
                    'save_folder_number': None,
                    'remote_ftp_path': namespace,
                    'smb_path': namespace,
                    'path_index': None
                },
                worker_id
            )
            guest.pending_deletion = True
            guest.save(update_fields=['pending_deletion'])
            self.stdout.write(f"Queued cleanup for expired guest: {guest.username}")

    def _get_any_worker(self, redis_client):
        worker_keys = redis_client.keys('worker:*')
        for key in worker_keys:
            key_str = key.decode() if isinstance(key, (bytes, bytearray)) else str(key)
            parts = key_str.split(':')
            if len(parts) != 2:
                continue
            client_id = parts[1]
            if redis_client.exists(f'worker:{client_id}'):
                return client_id
        return None
