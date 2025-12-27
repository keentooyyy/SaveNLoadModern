from django.apps import AppConfig
import threading
import time
import os
import sys

def worker_cleanup_loop():
    """Background thread to clean up offline workers"""

    
    from SaveNLoad.models.client_worker import ClientWorker
    print("Worker cleanup thread started")
    
    while True:
        try:
            # Run cleanup every 30 seconds
            ClientWorker.unclaim_offline_workers()
        except Exception as e:
            print(f"Cleanup error: {e}")
        time.sleep(30)

class SavenloadConfig(AppConfig):
    name = 'SaveNLoad'

    def ready(self):
        # Run in two cases:
        # 1. Django dev server reloader process (RUN_MAIN='true')
        # 2. Gunicorn worker process (sys.argv[0] contains 'gunicorn')
        # Avoid running in management commands like migrate/collectstatic
        
        is_runserver = os.environ.get('RUN_MAIN') == 'true'
        is_gunicorn = 'gunicorn' in sys.argv[0]
        
        if is_runserver or is_gunicorn:
            # Start background thread
            t = threading.Thread(target=worker_cleanup_loop, daemon=True)
            t.start()
