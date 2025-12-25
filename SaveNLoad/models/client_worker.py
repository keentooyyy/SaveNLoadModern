"""
Client Worker model to track connected workers
Each PC has a unique client_id for tracking
"""
from django.db import models
from django.utils import timezone

# Worker timeout: 6 seconds allows for 1 missed heartbeat (5s) + small network delay
# Heartbeats are sent every 5 seconds, so 6s detects offline immediately after one missed heartbeat
WORKER_TIMEOUT_SECONDS = 6


class ClientWorker(models.Model):
    """Tracks connected client workers - supports multiple concurrent clients
    Each PC must have a unique client_id for tracking purposes
    """
    
    client_id = models.CharField(max_length=255, unique=True, help_text="Unique identifier for the PC/client")
    last_heartbeat = models.DateTimeField(auto_now=True, help_text="Last time worker sent heartbeat")
    is_active = models.BooleanField(default=True, help_text="Whether worker is currently active")
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Constants
    WORKER_TIMEOUT_SECONDS = WORKER_TIMEOUT_SECONDS
    
    # Association field
    user = models.ForeignKey('SimpleUsers', on_delete=models.SET_NULL, null=True, blank=True, 
                            related_name='client_workers', help_text="User who owns this worker")
    
    class Meta:
        db_table = 'client_workers'
        verbose_name = 'Client Worker'
        verbose_name_plural = 'Client Workers'
        ordering = ['-last_heartbeat']
    
    def __str__(self):
        user_str = f" - {self.user.username}" if self.user else " (Unclaimed)"
        return f"{self.client_id}{user_str} ({'Active' if self.is_active else 'Inactive'})"
    
    def is_online(self, timeout_seconds: int = WORKER_TIMEOUT_SECONDS) -> bool:
        """Check if worker is online based on last heartbeat"""
        if not self.is_active:
            return False
        time_since_heartbeat = timezone.now() - self.last_heartbeat
        return time_since_heartbeat.total_seconds() < timeout_seconds
    
    @classmethod
    def get_active_workers(cls, timeout_seconds: int = WORKER_TIMEOUT_SECONDS):
        """Get all active workers that are currently online"""
        # Filter directly in database query for better performance and accuracy
        from datetime import timedelta
        timeout_threshold = timezone.now() - timedelta(seconds=timeout_seconds)
        return list(cls.objects.filter(
            is_active=True,
            last_heartbeat__gte=timeout_threshold
        ))
    
    @classmethod
    def get_worker_by_id(cls, client_id: str, timeout_seconds: int = WORKER_TIMEOUT_SECONDS):
        """Get a specific worker by client_id if it's online"""
        try:
            worker = cls.objects.get(client_id=client_id, is_active=True)
            if worker.is_online(timeout_seconds):
                return worker
        except cls.DoesNotExist:
            pass
        return None
    
    @classmethod
    def get_any_active_worker(cls, timeout_seconds: int = WORKER_TIMEOUT_SECONDS):
        """Get any active worker (for operations that don't need specific client)"""
        active_workers = cls.get_active_workers(timeout_seconds)
        return active_workers[0] if active_workers else None
    
    @classmethod
    def is_worker_connected(cls, timeout_seconds: int = WORKER_TIMEOUT_SECONDS) -> bool:
        """Check if any worker is connected and active"""
        # Direct database query for better performance
        from datetime import timedelta
        timeout_threshold = timezone.now() - timedelta(seconds=timeout_seconds)
        return cls.objects.filter(
            is_active=True,
            last_heartbeat__gte=timeout_threshold
        ).exists()
    
    @classmethod
    def cleanup_stale_workers(cls, timeout_seconds: int = WORKER_TIMEOUT_SECONDS):
        """Unclaim workers that have timed out"""
        from datetime import timedelta
        timeout_threshold = timezone.now() - timedelta(seconds=timeout_seconds)
        
        # Find workers that are owned but haven't heartbeated recently
        stale_workers = cls.objects.filter(
            user__isnull=False,
            last_heartbeat__lt=timeout_threshold
        )
        
        # Update them to be unclaimed
        count = stale_workers.update(user=None, is_active=False)
        return count

