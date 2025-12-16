"""
Client Worker model to track connected workers
Each PC has a unique client_id for tracking
"""
from django.db import models
from django.utils import timezone


class ClientWorker(models.Model):
    """Tracks connected client workers - supports multiple concurrent clients
    Each PC must have a unique client_id for tracking purposes
    """
    
    client_id = models.CharField(max_length=255, unique=True, help_text="Unique identifier for the PC/client")
    last_heartbeat = models.DateTimeField(auto_now=True, help_text="Last time worker sent heartbeat")
    is_active = models.BooleanField(default=True, help_text="Whether worker is currently active")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'client_workers'
        verbose_name = 'Client Worker'
        verbose_name_plural = 'Client Workers'
        ordering = ['-last_heartbeat']
    
    def __str__(self):
        return f"{self.client_id} ({'Active' if self.is_active else 'Inactive'})"
    
    def is_online(self, timeout_seconds: int = 30) -> bool:
        """Check if worker is online based on last heartbeat"""
        if not self.is_active:
            return False
        time_since_heartbeat = timezone.now() - self.last_heartbeat
        return time_since_heartbeat.total_seconds() < timeout_seconds
    
    @classmethod
    def get_active_workers(cls, timeout_seconds: int = 30):
        """Get all active workers that are currently online"""
        workers = cls.objects.filter(is_active=True)
        return [w for w in workers if w.is_online(timeout_seconds)]
    
    @classmethod
    def get_worker_by_id(cls, client_id: str, timeout_seconds: int = 30):
        """Get a specific worker by client_id if it's online"""
        try:
            worker = cls.objects.get(client_id=client_id, is_active=True)
            if worker.is_online(timeout_seconds):
                return worker
        except cls.DoesNotExist:
            pass
        return None
    
    @classmethod
    def get_any_active_worker(cls, timeout_seconds: int = 30):
        """Get any active worker (for operations that don't need specific client)"""
        active_workers = cls.get_active_workers(timeout_seconds)
        return active_workers[0] if active_workers else None
    
    @classmethod
    def is_worker_connected(cls, timeout_seconds: int = 30) -> bool:
        """Check if any worker is connected and active"""
        return len(cls.get_active_workers(timeout_seconds)) > 0

