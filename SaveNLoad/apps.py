from django.apps import AppConfig
import threading


class SavenloadConfig(AppConfig):
    name = 'SaveNLoad'

    def ready(self):
        # Start background thread to listen for Redis keyspace notifications
        # Real-time cleanup: when worker heartbeat expires, automatically unclaim the worker
        if not hasattr(self, '_cleanup_thread_started'):
            self._cleanup_thread_started = True
            
            def realtime_cleanup_listener():
                """Background thread that listens for Redis keyspace notifications for real-time cleanup"""
                from SaveNLoad.services.redis_worker_service import unclaim_worker
                from SaveNLoad.utils.redis_client import get_redis_client
                import redis
                
                try:
                    redis_client = get_redis_client()
                    
                    # Enable keyspace notifications for expired events (REQUIRED - no fallback)
                    # This allows us to get notified when keys expire
                    redis_client.config_set('notify-keyspace-events', 'Ex')
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
                    
                    # Subscribe to expired events for worker heartbeat keys
                    # Use __keyevent@<db>__:expired channel - this sends the key name as data
                    # This is more reliable than __keyspace@<db>__:worker:* pattern
                    keyevent_pattern = f'__keyevent@{redis_db}__:expired'
                    pubsub = pubsub_client.pubsub()
                    pubsub.psubscribe(keyevent_pattern)
                    
                    print(f"Real-time worker cleanup listener started (Redis keyspace notifications)")
                    print(f"DEBUG: Subscribed to keyevent pattern: {keyevent_pattern}")
                    
                    # Verify subscription worked
                    for message in pubsub.listen():
                        # Handle subscription confirmation
                        if message['type'] == 'psubscribe':
                            print(f"DEBUG: Successfully subscribed to pattern: {message['channel']}")
                            continue
                        
                        # Debug: log all messages to see what we're receiving
                        if message['type'] == 'pmessage':
                            channel = message['channel']
                            key_name = message['data']  # In keyevent, data is the key name
                            print(f"DEBUG: Received keyevent notification - channel: {channel}, expired key: {key_name}")
                            
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
                                    print(f"DEBUG: Worker heartbeat expired for {client_id}")
                                    
                                    # Check if worker has a user_id set (is claimed)
                                    try:
                                        user_id = redis_client.hget(f'worker:{client_id}:info', 'user_id')
                                        print(f"DEBUG: Worker {client_id} user_id: {user_id}")
                                        if user_id and user_id != '':
                                            # Worker heartbeat expired and it's still claimed - unclaim it
                                            unclaim_worker(client_id)
                                            print(f"Real-time cleanup: Auto-unclaimed offline worker {client_id}")
                                        else:
                                            print(f"DEBUG: Worker {client_id} not claimed, skipping unclaim")
                                    except Exception as e:
                                        print(f"Error auto-unclaiming offline worker {client_id}: {e}")
                                else:
                                    print(f"DEBUG: Ignoring expired sub-key: {key_name}")
                            else:
                                print(f"DEBUG: Ignoring expired key (not a worker key): {key_name}")
                        else:
                            # Log other message types for debugging
                            print(f"DEBUG: Received message type: {message['type']}, channel: {message.get('channel', 'N/A')}, data: {message.get('data', 'N/A')}")
                                    
                except redis.ConnectionError:
                    print("Error: Redis connection lost in cleanup listener")
                except Exception as e:
                    print(f"Error in real-time cleanup listener: {e}")
            
            # Start cleanup thread as daemon (won't prevent Django shutdown)
            cleanup_thread = threading.Thread(target=realtime_cleanup_listener, daemon=True)
            cleanup_thread.start()
            print("Real-time worker cleanup thread started (listening for Redis keyspace notifications)")
