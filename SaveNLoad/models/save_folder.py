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
    smb_path = models.CharField(max_length=500, blank=True, null=True, help_text="Full remote path (e.g., username/gamename/save_1) - FTP path format with forward slashes")
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
        """Override save to auto-populate remote path if missing"""
        if not self.smb_path:
            self.smb_path = self._generate_remote_path(self.user.username, self.game.name, self.folder_number)
        super().save(*args, **kwargs)
    
    @property
    def folder_name(self) -> str:
        """Get the folder name (e.g., 'save_1')"""
        return f"save_{self.folder_number}"
    
    @staticmethod
    def _generate_remote_path(username: str, game_name: str, folder_number: int) -> str:
        """Generate the full remote path for a save folder in FTP format (forward slashes)"""
        # Sanitize game name
        from SaveNLoad.utils.path_utils import sanitize_game_name
        safe_game_name = sanitize_game_name(game_name)
        # Generate full path in FTP format: username/gamename/save_1
        return f"{username}/{safe_game_name}/save_{folder_number}"
    
    @classmethod
    def get_or_create_next(cls, user: SimpleUsers, game: Game) -> 'SaveFolder':
        """
        Get the next available save folder, creating a new one if needed (sequential numbering).
        
        Uses sequential numbering (highest + 1) instead of reusing deleted slots.
        This prevents conflicts with empty folders left on FTP server.
        """
        # Get the highest existing folder number (sequential numbering)
        max_folder = cls.objects.filter(user=user, game=game).aggregate(
            max_num=models.Max('folder_number')
        )['max_num']
        
        # Count existing folders
        existing_count = cls.objects.filter(user=user, game=game).count()
        
        # If we have max folders, reuse the oldest one
        if existing_count >= cls.MAX_SAVE_FOLDERS:
            oldest_folder = cls.objects.filter(user=user, game=game).order_by('created_at').first()
            if oldest_folder:
                # Reset created_at for reuse and update remote path (in case game name changed)
                oldest_folder.created_at = timezone.now()
                oldest_folder.smb_path = cls._generate_remote_path(user.username, game.name, oldest_folder.folder_number)
                oldest_folder.save(update_fields=['created_at', 'smb_path'])
                return oldest_folder
        
        # Use next sequential number (highest + 1, or 1 if none exist)
        # This ensures we don't reuse deleted slots, preventing conflicts with empty folders
        next_number = (max_folder + 1) if max_folder else 1
        
        # Generate remote path
        smb_path = cls._generate_remote_path(user.username, game.name, next_number)
        
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
    

