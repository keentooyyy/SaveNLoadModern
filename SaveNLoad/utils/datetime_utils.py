"""
DateTime serialization and formatting utilities
"""
from django.utils import timezone
from datetime import timedelta, datetime


def to_isoformat(dt, default=None):
    """
    Convert datetime to ISO format string, handling None
    
    Used extensively in:
    - API responses
    - JSON serialization
    
    Args:
        dt: Datetime object or None
        default: Default value if dt is None
        
    Returns:
        ISO format string or default
    """
    if dt is None:
        return default
    if hasattr(dt, 'isoformat'):
        return dt.isoformat()
    return default


def get_time_threshold(seconds: int = None, minutes: int = None, hours: int = None, days: int = None):
    """
    Get time threshold (now - timedelta) for timeout checks
    
    Used in:
    - Operation timeout checks
    - Worker ping checks
    - OTP expiration checks
    
    Args:
        seconds: Seconds ago
        minutes: Minutes ago
        hours: Hours ago
        days: Days ago
        
    Returns:
        Datetime threshold
    """
    if days:
        return timezone.now() - timedelta(days=days)
    elif hours:
        return timezone.now() - timedelta(hours=hours)
    elif minutes:
        return timezone.now() - timedelta(minutes=minutes)
    elif seconds:
        return timezone.now() - timedelta(seconds=seconds)
    else:
        return timezone.now()


def calculate_progress_percentage(current: int, total: int, status: str = None) -> int:
    """
    Calculate progress percentage from current/total with status fallback
    
    Used in:
    - Operation status checking
    - Progress bar updates
    
    Args:
        current: Current progress count
        total: Total items
        status: Optional status string ('completed', 'failed', etc.)
        
    Returns:
        Progress percentage (0-100)
    """
    if total > 0:
        return min(100, int((current / total) * 100))
    elif status == 'completed':
        return 100
    elif status == 'failed':
        return 0
    else:
        return 0

