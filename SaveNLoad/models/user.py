from django.db import models
from django.contrib.auth.hashers import make_password, check_password


# Role constants
class UserRole:
    ADMIN = 'admin'
    USER = 'user'
    
    CHOICES = [
        (ADMIN, 'Admin'),
        (USER, 'User'),
    ]


class SimpleUsers(models.Model):
    """Custom User model - completely independent from Django's auth system"""
    
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # Will store hashed password
    role = models.CharField(
        max_length=10,
        choices=UserRole.CHOICES,
        default=UserRole.USER
    )
    pending_deletion = models.BooleanField(default=False, help_text="If True, user is marked for deletion and will be deleted after all FTP cleanup operations complete")
    last_authenticated_request = models.DateTimeField(null=True, blank=True, help_text="Last time user made an authenticated request - used to detect cookie clearing")
    
    class Meta:
        db_table = 'simple_users'
        verbose_name = 'Simple User'
        verbose_name_plural = 'Simple Users'
    
    def __str__(self):
        return self.username
    
    def set_password(self, raw_password):
        """Hash and set the password"""
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        """Check if the provided password matches"""
        return check_password(raw_password, self.password)
    
    def is_admin(self):
        """Check if user is an admin"""
        return self.role == UserRole.ADMIN
    
    def is_user(self):
        """Check if user is a regular user"""
        return self.role == UserRole.USER

