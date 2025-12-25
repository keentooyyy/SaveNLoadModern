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
        status = "Online" if self.is_online() else "Offline"
        return f"{self.client_id}{user_str} ({status})"
    
    def is_online(self, timeout_seconds: int = WORKER_TIMEOUT_SECONDS) -> bool:
        """Check if worker is online based on last heartbeat"""
        # Rely purely on heartbeat timestamp as the source of truth
        if not self.last_heartbeat:
            return False
        time_since_heartbeat = timezone.now() - self.last_heartbeat
        return time_since_heartbeat.total_seconds() < timeout_seconds
    
    @classmethod
    def get_active_workers(cls, timeout_seconds: int = WORKER_TIMEOUT_SECONDS):
        """Get all active workers that are currently online"""
        # Filter directly in database query for better performance and accuracy
        # We rely solely on the heartbeat timestamp as the source of truth
        from datetime import timedelta
        timeout_threshold = timezone.now() - timedelta(seconds=timeout_seconds)
        return list(cls.objects.filter(
            last_heartbeat__gte=timeout_threshold
        ))
    
    @classmethod
    def get_worker_by_id(cls, client_id: str, timeout_seconds: int = WORKER_TIMEOUT_SECONDS):
        """Get a specific worker by client_id if it's online"""
        try:
            worker = cls.objects.get(client_id=client_id)
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
            last_heartbeat__gte=timeout_threshold
        ).exists()
    
    @classmethod
    def unclaim_offline_workers(cls, timeout_seconds: int = 25):
        """
        Automatically unclaim workers that have gone offline.
        This allows users to claim other workers or allows workers to be claimed by others.
        Uses 25 second timeout (5 heartbeats * 5 seconds) to give workers more time before unclaiming.
        """
        from datetime import timedelta
        timeout_threshold = timezone.now() - timedelta(seconds=timeout_seconds)
        
        # Find workers that are claimed but haven't heartbeated recently
        offline_workers = cls.objects.filter(
            user__isnull=False,  # Only workers that are claimed
            last_heartbeat__lt=timeout_threshold
        )
        
        # Unclaim them
        count = offline_workers.update(user=None)
        if count > 0:
            print(f"Auto-unclaimed {count} offline worker(s)")
        return count

