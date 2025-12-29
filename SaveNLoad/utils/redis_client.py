"""
Redis connection management utility
"""
import redis
from django.conf import settings
import threading

# Thread-local storage for Redis connections
_thread_local = threading.local()


def get_redis_client():
    """
    Get Redis client instance (thread-safe, reuses connection per thread)
    Returns: redis.Redis client instance
    """
    if not hasattr(_thread_local, 'redis_client'):
        # Create Redis connection
        if settings.REDIS_PASSWORD:
            _thread_local.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
        else:
            _thread_local.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
        
        # Test connection
        try:
            _thread_local.redis_client.ping()
        except redis.ConnectionError as e:
            print(f"ERROR: Failed to connect to Redis: {e}")
            raise
    
    return _thread_local.redis_client


def get_redis_pubsub():
    """
    Get Redis Pub/Sub instance for subscribing to channels
    Returns: redis.client.PubSub instance
    """
    client = get_redis_client()
    return client.pubsub()

