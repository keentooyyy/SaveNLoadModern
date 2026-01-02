"""
Save Folder model for tracking save folders on remote storage
"""
from django.db import models
from django.utils import timezone
from SaveNLoad.models.user import SimpleUsers
from SaveNLoad.models.game import Game
from SaveNLoad.utils.path_utils import generate_save_folder_path


class SaveFolder(models.Model):
    """
    Tracks save folders for user+game combinations on remote storage.

    Args:
        None

    Returns:
        None
    """
    
    MAX_SAVE_FOLDERS = 10
    
    user = models.ForeignKey(SimpleUsers, on_delete=models.CASCADE, related_name='save_folders')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='save_folders')
    folder_number = models.IntegerField(help_text="Save folder number (1-10)")
    smb_path = models.CharField(max_length=500, blank=True, null=True, help_text="Full remote path (e.g., username/gamename/save_1) - Remote path format with forward slashes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'save_folders'
        verbose_name = 'Save Folder'
        verbose_name_plural = 'Save Folders'
        unique_together = [['user', 'game', 'folder_number']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'game', '-created_at']),
        ]
    
    def __str__(self):
        """
        Return a human-readable identifier for the save folder.

        Args:
            None

        Returns:
            Save folder path string.
        """
        return f"{self.user.username}/{self.game.name}/save_{self.folder_number}"
    
    def save(self, *args, **kwargs):
        """
        Override save to autopopulate remote path if missing.

        Args:
            *args: Positional args passed to Model.save.
            **kwargs: Keyword args passed to Model.save.

        Returns:
            None
        """
        if not self.smb_path:
            # Ensure remote path is always available for worker operations.
            self.smb_path = generate_save_folder_path(self.user.username, self.game.name, self.folder_number)
        super().save(*args, **kwargs)
    
    @property
    def folder_name(self) -> str:
        """
        Get the folder name (e.g., 'save_1').

        Args:
            None

        Returns:
            Folder name string.
        """
        return f"save_{self.folder_number}"
    
    @classmethod
    def get_or_create_next(cls, user: SimpleUsers, game: Game) -> 'SaveFolder':
        """
        Get the next available save folder, creating a new one if needed.
        
        Strategy:
        1. If we have less than MAX_SAVE_FOLDERS, fill available slots (1-10) first
        2. Only when all 10 slots are used, reuse the oldest one

        Args:
            user: User that owns the save folder.
            game: Game associated with the save folder.

        Returns:
            SaveFolder instance to use for the next save.
        """
        # Get all existing folder numbers
        existing_numbers = set(
            cls.objects.filter(user=user, game=game)
            .values_list('folder_number', flat=True)
        )
        
        existing_count = len(existing_numbers)
        
        # If we have max folders, reuse the oldest one
        if existing_count >= cls.MAX_SAVE_FOLDERS:
            oldest_folder = cls.objects.filter(user=user, game=game).order_by('created_at').first()
            if oldest_folder:
                # Reset created_at for reuse and refresh smb_path in case game name changed.
                oldest_folder.created_at = timezone.now()
                oldest_folder.smb_path = generate_save_folder_path(user.username, game.name, oldest_folder.folder_number)
                oldest_folder.save(update_fields=['created_at', 'smb_path'])
                return oldest_folder
        
        # Find the first available slot (1-10) - fills gaps first
        # This ensures we stay within MAX_SAVE_FOLDERS limit
        next_number = 1
        for i in range(1, cls.MAX_SAVE_FOLDERS + 1):
            if i not in existing_numbers:
                next_number = i
                break
        
        # Generate remote path
        smb_path = generate_save_folder_path(user.username, game.name, next_number)
        
        # Create new save folder
        save_folder = cls.objects.create(
            user=user,
            game=game,
            folder_number=next_number,
            smb_path=smb_path
        )
        return save_folder
    
    @classmethod
    def get_latest(cls, user: SimpleUsers, game: Game) -> 'SaveFolder':
        """
        Get the most recently created save folder for a user+game.

        Args:
            user: User that owns the save folder.
            game: Game associated with the save folder.

        Returns:
            Most recently created SaveFolder or None.
        """
        return cls.objects.filter(user=user, game=game).order_by('-created_at').first()
    
    @classmethod
    def get_by_number(cls, user: SimpleUsers, game: Game, folder_number: int) -> 'SaveFolder':
        """
        Get a specific save folder by number.

        Args:
            user: User that owns the save folder.
            game: Game associated with the save folder.
            folder_number: Save folder number (1-10).

        Returns:
            SaveFolder instance if found, otherwise None.
        """
        try:
            return cls.objects.get(user=user, game=game, folder_number=folder_number)
        except cls.DoesNotExist:
            return None
    

