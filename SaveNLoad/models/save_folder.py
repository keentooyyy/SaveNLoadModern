"""
Save Folder model for tracking save folders on FTP server
"""
from django.db import models
from django.utils import timezone
from SaveNLoad.models.user import SimpleUsers
from SaveNLoad.models.game import Game


class SaveFolder(models.Model):
    """Tracks save folders for user+game combinations on FTP server"""
    
    MAX_SAVE_FOLDERS = 10
    
    user = models.ForeignKey(SimpleUsers, on_delete=models.CASCADE, related_name='save_folders')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='save_folders')
    folder_number = models.IntegerField(help_text="Save folder number (1-10)")
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
        return f"{self.user.username}/{self.game.name}/save_{self.folder_number}"
    
    @property
    def folder_name(self) -> str:
        """Get the folder name (e.g., 'save_1')"""
        return f"save_{self.folder_number}"
    
    @classmethod
    def get_or_create_next(cls, user: SimpleUsers, game: Game) -> 'SaveFolder':
        """Get the next available save folder, creating a new one if needed (optimized)"""
        # Single query to get all existing folder numbers
        existing_numbers = set(
            cls.objects.filter(user=user, game=game)
            .values_list('folder_number', flat=True)
        )
        
        # If we have max folders, reuse the oldest one
        if len(existing_numbers) >= cls.MAX_SAVE_FOLDERS:
            oldest_folder = cls.objects.filter(user=user, game=game).order_by('created_at').first()
            if oldest_folder:
                # Reset created_at for reuse
                oldest_folder.created_at = timezone.now()
                oldest_folder.save(update_fields=['created_at'])
                return oldest_folder
        
        # Find the next available number
        next_number = 1
        for i in range(1, cls.MAX_SAVE_FOLDERS + 1):
            if i not in existing_numbers:
                next_number = i
                break
        
        # Create new save folder
        save_folder = cls.objects.create(
            user=user,
            game=game,
            folder_number=next_number
        )
        return save_folder
    
    @classmethod
    def get_latest(cls, user: SimpleUsers, game: Game) -> 'SaveFolder':
        """Get the most recently created save folder for a user+game"""
        return cls.objects.filter(user=user, game=game).order_by('-created_at').first()
    
    @classmethod
    def get_by_number(cls, user: SimpleUsers, game: Game, folder_number: int) -> 'SaveFolder':
        """Get a specific save folder by number"""
        try:
            return cls.objects.get(user=user, game=game, folder_number=folder_number)
        except cls.DoesNotExist:
            return None
    

