"""
Password Reset OTP model for storing one-time passwords
"""
from django.db import models
from django.db.models import Q
from django.utils import timezone
from SaveNLoad.models.user import SimpleUsers
import secrets
from datetime import timedelta


class PasswordResetOTP(models.Model):
    """Stores OTP codes for password reset"""
    
    user = models.ForeignKey(SimpleUsers, on_delete=models.CASCADE, related_name='password_reset_otps')
    otp_code = models.CharField(max_length=6, help_text="6-digit OTP code")
    email = models.EmailField(help_text="Email address the OTP was sent to")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="OTP expiration time")
    is_used = models.BooleanField(default=False, help_text="Whether OTP has been used")
    
    class Meta:
        db_table = 'password_reset_otps'
        verbose_name = 'Password Reset OTP'
        verbose_name_plural = 'Password Reset OTPs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['otp_code', 'is_used', 'expires_at']),
            models.Index(fields=['user', 'is_used']),
        ]
    
    def __str__(self):
        return f"OTP for {self.user.username} ({'used' if self.is_used else 'active'})"
    
    @classmethod
    def generate_otp(cls, user: SimpleUsers, email: str, expiry_minutes: int = 10) -> 'PasswordResetOTP':
        """Generate a new OTP for password reset - ONLY for registered email addresses"""
        # Security: Ensure email matches the user's registered email
        if email.lower() != user.email.lower():
            raise ValueError(f"Email {email} does not match registered email {user.email} for user {user.username}")
        
        # Generate 6-digit OTP
        otp_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        
        # Set expiration time
        expires_at = timezone.now() + timedelta(minutes=expiry_minutes)
        
        # Invalidate any existing unused OTPs for this user
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        
        # Cleanup expired/used OTPs immediately to prevent database bloat
        cls.cleanup_otps()
        
        # Create new OTP using the user's registered email
        otp = cls.objects.create(
            user=user,
            otp_code=otp_code,
            email=user.email,  # Always use the registered email from database
            expires_at=expires_at
        )
        
        return otp
    
    def is_valid(self) -> bool:
        """Check if OTP is still valid (not used and not expired)"""
        if self.is_used:
            return False
        if timezone.now() > self.expires_at:
            return False
        return True
    
    def mark_as_used(self):
        """Mark OTP as used and cleanup expired/used OTPs"""
        self.is_used = True
        self.save(update_fields=['is_used'])
        # Cleanup expired/used OTPs after marking as used
        self.__class__.cleanup_otps()
    
    @classmethod
    def validate_otp(cls, email: str, otp_code: str) -> 'PasswordResetOTP':
        """Validate OTP code and return the OTP object if valid"""
        # Cleanup expired/used OTPs before validation
        cls.cleanup_otps()
        
        try:
            otp = cls.objects.get(
                email__iexact=email,
                otp_code=otp_code,
                is_used=False
            )
            
            if otp.is_valid():
                return otp
            else:
                return None
        except cls.DoesNotExist:
            return None
        except cls.MultipleObjectsReturned:
            # If multiple OTPs exist, get the most recent one
            otp = cls.objects.filter(
                email__iexact=email,
                otp_code=otp_code,
                is_used=False
            ).order_by('-created_at').first()
            
            if otp and otp.is_valid():
                return otp
            return None
    
    @classmethod
    def cleanup_otps(cls) -> int:
        """
        Clean up all expired or used OTPs immediately
        Called automatically during OTP operations to keep database clean
        
        Returns:
            Number of OTPs deleted
        """
        # Delete all expired or used OTPs immediately
        deleted_count, _ = cls.objects.filter(
            Q(is_used=True) | Q(expires_at__lt=timezone.now())
        ).delete()
        
        return deleted_count

