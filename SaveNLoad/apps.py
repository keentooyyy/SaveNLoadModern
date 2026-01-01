from django.apps import AppConfig
import threading


class SavenloadConfig(AppConfig):
    name = 'SaveNLoad'
    _cleanup_thread_started = False
    _cleanup_lock = threading.Lock()

    def ready(self):
        # Start background thread to listen for Redis keyspace notifications
        # Real-time cleanup: when worker heartbeat expires, automatically unclaim the worker
        with self._cleanup_lock:
            if self._cleanup_thread_started:
                return  # Already started
            self._cleanup_thread_started = True
            
            def realtime_cleanup_listener():
                """Background thread that listens for Redis keyspace notifications for real-time cleanup"""
                from SaveNLoad.services.redis_worker_service import unclaim_worker
                from SaveNLoad.utils.redis_client import get_redis_client
                import redis
                
                try:
                    redis_client = get_redis_client()
                    
                    # Enable keyspace notifications for expired + delete events.
                    # 'E' = keyevent, 'x' = expired, 'g' = generic (DEL).
                    redis_client.config_set('notify-keyspace-events', 'Exg')
                    # Verify it was set
                    current_config = redis_client.config_get('notify-keyspace-events')
                    print(f"Redis keyspace notifications enabled: {current_config.get('notify-keyspace-events', 'NOT SET')}")
                    
                    # Get Redis DB number from settings
                    from django.conf import settings
                    redis_db = settings.REDIS_DB
                    
                    # Create a separate connection for pub/sub (can't use same connection)
                    redis_host = redis_client.connection_pool.connection_kwargs.get('host', 'localhost')
                    redis_port = redis_client.connection_pool.connection_kwargs.get('port', 6379)
                    redis_password = redis_client.connection_pool.connection_kwargs.get('password')
                    
                    pubsub_client = redis.Redis(
                        host=redis_host,
                        port=redis_port,
                        db=redis_db,
                        password=redis_password,
                        decode_responses=True
                    )
                    
                    # Subscribe to expired + delete events for worker heartbeat keys
                    # Use __keyevent@<db>__:expired|del channels - data is the key name
                    # This is more reliable than __keyspace@<db>__:worker:* pattern
                    keyevent_patterns = [
                        f'__keyevent@{redis_db}__:expired',
                        f'__keyevent@{redis_db}__:del',
                    ]
                    pubsub = pubsub_client.pubsub()
                    for pattern in keyevent_patterns:
                        pubsub.psubscribe(pattern)
                    
                    print(f"Real-time worker cleanup listener started (Redis keyspace notifications)")
                    
                    # Track processed keys to prevent duplicate processing (thread-safe)
                    processed_keys = set()
                    processing_lock = threading.Lock()
                    
                    # Verify subscription worked
                    for message in pubsub.listen():
                        # Handle subscription confirmation
                        if message['type'] == 'psubscribe':
                            continue
                        
                        # Process expired key notifications
                        if message['type'] == 'pmessage':
                            channel = message['channel']
                            key_name = message['data']  # In keyevent, data is the key name
                            try:
                                event_name = str(channel).split(':', 1)[1]
                            except Exception:
                                event_name = str(channel)
                            
                            # Prevent duplicate processing with thread-safe check
                            with processing_lock:
                                if key_name in processed_keys:
                                    continue  # Already processed
                                processed_keys.add(key_name)
                                
                                # Clean up old processed keys (keep last 1000 to prevent memory leak)
                                if len(processed_keys) > 1000:
                                    processed_keys.clear()
                            
                            # Check if this is a worker heartbeat key
                            # Worker heartbeat keys: worker:{client_id} (client_id can contain colons)
                            # Sub-keys: worker:{client_id}:info, worker:{client_id}:operations, worker:{client_id}:notify
                            if key_name.startswith('worker:'):
                                # Remove 'worker:' prefix
                                suffix = key_name[7:]  # len('worker:') = 7
                                
                                # Check if it's a sub-key by looking for known suffixes
                                # Sub-keys end with :info, :operations, or :notify
                                is_sub_key = (suffix.endswith(':info') or 
                                            suffix.endswith(':operations') or 
                                            suffix.endswith(':notify'))
                                
                                if not is_sub_key:
                                    # This is a worker heartbeat key
                                    client_id = suffix
                                    
                                    # Check if worker has a user_id set (is claimed)
                                    try:
                                        user_id = redis_client.hget(f'worker:{client_id}:info', 'user_id')
                                        if user_id and user_id != '':
                                            # Worker heartbeat expired and it's still claimed - unclaim it
                                            # Double-check with lock to prevent duplicate unclaim
                                            with processing_lock:
                                                # Check if we already processed this client_id
                                                if f'unclaimed_{client_id}' in processed_keys:
                                                    continue
                                                processed_keys.add(f'unclaimed_{client_id}')
                                            
                                            unclaim_worker(client_id)
                                            print(f"Real-time cleanup: event={event_name} key={key_name}")
                                            print(f"Real-time cleanup: Auto-unclaimed offline worker {client_id}")
                                    except Exception as e:
                                        print(f"Error auto-unclaiming offline worker {client_id}: {e}")
                                    
                except redis.ConnectionError:
                    print("Error: Redis connection lost in cleanup listener")
                except Exception as e:
                    print(f"Error in real-time cleanup listener: {e}")
            
            # Start cleanup thread as daemon (won't prevent Django shutdown)
            cleanup_thread = threading.Thread(target=realtime_cleanup_listener, daemon=True)
            cleanup_thread.start()
            print("Real-time worker cleanup thread started (listening for Redis keyspace notifications)")
