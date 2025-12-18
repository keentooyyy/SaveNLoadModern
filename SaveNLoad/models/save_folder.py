"""
Save Folder model for tracking save folders on SMB/CIFS server
"""
from django.db import models
from django.utils import timezone
from SaveNLoad.models.user import SimpleUsers
from SaveNLoad.models.game import Game


class SaveFolder(models.Model):
    """Tracks save folders for user+game combinations on SMB/CIFS server"""
    
    MAX_SAVE_FOLDERS = 10
    
    user = models.ForeignKey(SimpleUsers, on_delete=models.CASCADE, related_name='save_folders')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='save_folders')
    folder_number = models.IntegerField(help_text="Save folder number (1-10)")
    smb_path = models.CharField(max_length=500, blank=True, null=True, help_text="Full SMB path (e.g., username\\gamename\\save_1) - Windows path format with backslashes")
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
    
    def save(self, *args, **kwargs):
        """Override save to auto-populate smb_path if missing"""
        if not self.smb_path:
            self.smb_path = self._generate_smb_path(self.user.username, self.game.name, self.folder_number)
        super().save(*args, **kwargs)
    
    @property
    def folder_name(self) -> str:
        """Get the folder name (e.g., 'save_1')"""
        return f"save_{self.folder_number}"
    
    @staticmethod
    def _generate_smb_path(username: str, game_name: str, folder_number: int) -> str:
        """Generate the full SMB path for a save folder in Windows format (backslashes)"""
        # Sanitize game name
        safe_game_name = "".join(c for c in game_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_game_name = safe_game_name.replace(' ', '_')
        # Generate full path in SMB/Windows format: username\gamename\save_1
        return f"{username}\\{safe_game_name}\\save_{folder_number}"
    
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
                # Reset created_at for reuse and update SMB path (in case game name changed)
                oldest_folder.created_at = timezone.now()
                oldest_folder.smb_path = cls._generate_smb_path(user.username, game.name, oldest_folder.folder_number)
                oldest_folder.save(update_fields=['created_at', 'smb_path'])
                return oldest_folder
        
        # Find the next available number
        next_number = 1
        for i in range(1, cls.MAX_SAVE_FOLDERS + 1):
            if i not in existing_numbers:
                next_number = i
                break
        
        # Generate SMB path
        smb_path = cls._generate_smb_path(user.username, game.name, next_number)
        
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
        """Get the most recently created save folder for a user+game"""
        return cls.objects.filter(user=user, game=game).order_by('-created_at').first()
    
    @classmethod
    def get_by_number(cls, user: SimpleUsers, game: Game, folder_number: int) -> 'SaveFolder':
        """Get a specific save folder by number"""
        try:
            return cls.objects.get(user=user, game=game, folder_number=folder_number)
        except cls.DoesNotExist:
            return None
    

