"""
Client Worker model to track connected workers
Each PC has a unique client_id for tracking
"""
from django.db import models
from django.utils import timezone
from django.contrib.sessions.models import Session

# ============================================================================
# WORKER AND SESSION TIMEOUT CONSTANTS
# ============================================================================
# All timeout values are centralized here for easy maintenance and tracking


# Worker timeout: 6 seconds allows for 1 missed heartbeat (5s) + small network delay
# Heartbeats are sent every 5 seconds, so 6s detects offline immediately after one missed heartbeat
WORKER_TIMEOUT_SECONDS = 6

# Server ping interval: 5 seconds
# How often workers should poll the ping endpoint
SERVER_PING_INTERVAL_SECONDS = 5

# Max missed pings: 2
# Unclaim after this many missed pings (10 seconds total = 2 × 5 seconds)
MAX_MISSED_PINGS = 2






class ClientWorker(models.Model):
    """Tracks connected client workers - supports multiple concurrent clients
    Each PC must have a unique client_id for tracking purposes
    """
    
    client_id = models.CharField(max_length=255, unique=True, help_text="Unique identifier for the PC/client")
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Ping tracking fields (replacing heartbeat system)
    last_ping_response = models.DateTimeField(null=True, blank=True, help_text="Last time worker called ping endpoint")
    missed_ping_count = models.IntegerField(default=0, help_text="Consecutive missed pings")
    is_offline = models.BooleanField(default=False, help_text="Explicit offline flag for UI")
    
    # Constants
    WORKER_TIMEOUT_SECONDS = WORKER_TIMEOUT_SECONDS
    
    # Association field
    user = models.ForeignKey('SimpleUsers', on_delete=models.SET_NULL, null=True, blank=True, 
                            related_name='client_workers', help_text="User who owns this worker")
    
    class Meta:
        db_table = 'client_workers'
        verbose_name = 'Client Worker'
        verbose_name_plural = 'Client Workers'
        ordering = ['-last_ping_response']
    
    def __str__(self):
        user_str = f" - {self.user.username}" if self.user else " (Unclaimed)"
        status = "Online" if self.is_online() else "Offline"
        return f"{self.client_id}{user_str} ({status})"
    
    def is_online(self, timeout_seconds: int = None) -> bool:
        """Check if worker is online based on ping data"""
        # Use ping data as the source of truth
        if self.is_offline:
            return False
        if self.missed_ping_count >= MAX_MISSED_PINGS:
            return False
        if not self.last_ping_response:
            return False
        # Check if last ping was recent (within 10 seconds = 2 × ping interval)
        from datetime import timedelta
        ping_threshold = timezone.now() - timedelta(seconds=SERVER_PING_INTERVAL_SECONDS * 2)
        return self.last_ping_response >= ping_threshold
    
    @classmethod
    def get_active_workers(cls, timeout_seconds: int = None):
        """Get all active workers that are currently online"""
        # Filter directly in database query for better performance and accuracy
        # We rely on ping data as the source of truth
        from datetime import timedelta
        ping_threshold = timezone.now() - timedelta(seconds=SERVER_PING_INTERVAL_SECONDS * 2)
        return list(cls.objects.filter(
            is_offline=False,
            missed_ping_count__lt=MAX_MISSED_PINGS,
            last_ping_response__gte=ping_threshold
        ))
    
    @classmethod
    def get_worker_by_id(cls, client_id: str, timeout_seconds: int = None):
        """Get a specific worker by client_id if it's online"""
        try:
            worker = cls.objects.get(client_id=client_id)
            if worker.is_online():
                return worker
        except cls.DoesNotExist:
            pass
        return None
    
    @classmethod
    def get_any_active_worker(cls, timeout_seconds: int = None):
        """Get any active worker (for operations that don't need specific client)"""
        active_workers = cls.get_active_workers()
        return active_workers[0] if active_workers else None
    
    @classmethod
    def is_worker_connected(cls, timeout_seconds: int = None) -> bool:
        """Check if any worker is connected and active"""
        # Direct database query for better performance
        from datetime import timedelta
        ping_threshold = timezone.now() - timedelta(seconds=SERVER_PING_INTERVAL_SECONDS * 2)
        return cls.objects.filter(
            is_offline=False,
            missed_ping_count__lt=MAX_MISSED_PINGS,
            last_ping_response__gte=ping_threshold
        ).exists()
    
    @classmethod
    def check_claimed_workers(cls):
        """
        Check all claimed workers - check for offline workers (missed pings).
        
        This method:
        1. Checks if workers have pinged recently (within last 10 seconds)
        2. Calculates missed ping count based on actual time elapsed
        3. Unclaims workers that are offline (missed 2+ pings)
        
        Returns:
            offline_count - number of workers unclaimed
        """
        from datetime import timedelta
        
        # Get all claimed workers
        claimed_workers = cls.objects.filter(user__isnull=False)
        
        # Threshold: if worker hasn't pinged in last 10 seconds, consider it missed
        ping_threshold = timezone.now() - timedelta(seconds=SERVER_PING_INTERVAL_SECONDS * 2)
        
        offline_count = 0
        now = timezone.now()
        
        for worker in claimed_workers:
            # Check if worker has pinged recently
            if worker.last_ping_response and worker.last_ping_response >= ping_threshold:
                # Worker is alive (pinged recently) - reset missed count
                worker.missed_ping_count = 0
                worker.is_offline = False
                worker.save()
            else:
                # Worker hasn't pinged recently - calculate missed pings based on time elapsed
                if worker.last_ping_response:
                    # Calculate how many ping intervals have passed since last ping
                    time_since_last_ping = (now - worker.last_ping_response).total_seconds()
                    # Calculate expected missed pings (each ping interval is 5 seconds)
                    expected_missed = int(time_since_last_ping / SERVER_PING_INTERVAL_SECONDS)
                    # Cap at MAX_MISSED_PINGS to avoid counting beyond threshold
                    worker.missed_ping_count = min(expected_missed, MAX_MISSED_PINGS)
                else:
                    # No ping history - treat as missed
                    worker.missed_ping_count = MAX_MISSED_PINGS
                
                worker.save()
                
                if worker.missed_ping_count >= MAX_MISSED_PINGS:
                    # Too many missed pings - unclaim
                    worker.user = None
                    worker.is_offline = True
                    worker.save()
                    offline_count += 1
                    print(f"Unclaimed worker {worker.client_id} - offline (missed {MAX_MISSED_PINGS} pings)")
        
        if offline_count > 0:
            print(f"Auto-unclaimed {offline_count} offline worker(s)")
        
        return offline_count
