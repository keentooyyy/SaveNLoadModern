"""
Django management command to unclaim all workers
Usage: python manage.py unclaim_all_workers
"""
from django.core.management.base import BaseCommand
from SaveNLoad.services.redis_worker_service import get_online_workers, get_worker_info, unclaim_worker


class Command(BaseCommand):
    help = 'Unclaim all workers (nuke command for testing)'

    def handle(self, *args, **options):
        online_workers = get_online_workers()
        
        if not online_workers:
            self.stdout.write(self.style.WARNING('No online workers found.'))
            return
        
        self.stdout.write(f'Found {len(online_workers)} online worker(s).')
        
        unclaimed_count = 0
        for client_id in online_workers:
            worker_info = get_worker_info(client_id)
            if worker_info and worker_info.get('user_id'):
                try:
                    unclaim_worker(client_id)
                    unclaimed_count += 1
                    self.stdout.write(self.style.SUCCESS(f'Unclaimed: {client_id}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Failed to unclaim {client_id}: {e}'))
            else:
                self.stdout.write(f'Skipped (already unclaimed): {client_id}')
        
        self.stdout.write(self.style.SUCCESS(f'\nUnclaimed {unclaimed_count} worker(s).'))

