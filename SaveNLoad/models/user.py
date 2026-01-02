from django.contrib.auth.hashers import make_password, check_password
from django.db import models


# Role constants
class UserRole:
    """
    Role constants for SimpleUsers.

    Args:
        None

    Returns:
        None
    """
    ADMIN = 'admin'
    USER = 'user'
    
    # Keep choice tuples in sync with the constants above.
    CHOICES = [
        (ADMIN, 'Admin'),
        (USER, 'User'),
    ]


class SimpleUsers(models.Model):
    """
    Custom User model - completely independent of Django's auth system.

    Args:
        None

    Returns:
        None
    """
    
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
        """
        Return the display name for the user instance.

        Args:
            None

        Returns:
            Username string.
        """
        return self.username
    
    def set_password(self, raw_password):
        """
        Hash and set the password.

        Args:
            raw_password: Plaintext password to hash.

        Returns:
            None
        """
        # Store hashed password only.
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        """
        Check if the provided password matches.

        Args:
            raw_password: Plaintext password to verify.

        Returns:
            True if the password matches, False otherwise.
        """
        return check_password(raw_password, self.password)
    
    def is_admin(self):
        """
        Check if user is an admin.

        Args:
            None

        Returns:
            True if role is admin, False otherwise.
        """
        return self.role == UserRole.ADMIN
    
    def is_user(self):
        """
        Check if user is a regular user.

        Args:
            None

        Returns:
            True if role is user, False otherwise.
        """
        return self.role == UserRole.USER

