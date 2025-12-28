from django.apps import AppConfig
import threading
import time
import os
import sys

def worker_cleanup_loop():
    """Background thread to check claimed workers and unclaim offline/cookie-cleared workers"""
    
    from SaveNLoad.models.client_worker import ClientWorker, SERVER_PING_INTERVAL_SECONDS
    print("Worker cleanup thread started")
    
    while True:
        try:
            # Run check every 5 seconds to match ping interval
            ClientWorker.check_claimed_workers()
        except Exception as e:
            print(f"Cleanup error: {e}")
        time.sleep(SERVER_PING_INTERVAL_SECONDS)

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
