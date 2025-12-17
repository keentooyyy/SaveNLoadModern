"""
Password Reset OTP model for storing one-time passwords
"""
from django.db import models
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
        """Generate a new OTP for password reset"""
        # Generate 6-digit OTP
        otp_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        
        # Set expiration time
        expires_at = timezone.now() + timedelta(minutes=expiry_minutes)
        
        # Invalidate any existing unused OTPs for this user
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        
        # Create new OTP
        otp = cls.objects.create(
            user=user,
            otp_code=otp_code,
            email=email,
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
        """Mark OTP as used"""
        self.is_used = True
        self.save(update_fields=['is_used'])
    
    @classmethod
    def validate_otp(cls, email: str, otp_code: str) -> 'PasswordResetOTP':
        """Validate OTP code and return the OTP object if valid"""
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

