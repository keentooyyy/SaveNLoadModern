from django.db import models
import os


class Game(models.Model):
    """Game model for managing games and their save file locations"""
    
    name = models.CharField(max_length=255, unique=True)
    # Store cached local image file
    banner = models.ImageField(upload_to='game_banners/', blank=True, null=True, help_text="Cached local banner image file")
    # Keep original URL for reference and re-download if needed
    banner_url = models.URLField(max_length=500, blank=True, null=True, help_text="Original URL to the game banner/image (from RAWG API)")
    save_file_location = models.CharField(max_length=500, help_text="Path to the save file location")
    # Optional timestamp for when this game was last played (for future use in dashboards, sorting, etc.)
    last_played = models.DateTimeField(blank=True, null=True)
    pending_deletion = models.BooleanField(default=False, help_text="If True, game is marked for deletion and will be deleted after all FTP cleanup operations complete")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'games'
        verbose_name = 'Game'
        verbose_name_plural = 'Games'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_banner_url(self):
        """
        Returns the banner URL for display.
        Prioritizes local cached file, falls back to original URL if file doesn't exist.
        """
        if self.banner and self.banner.name:
            # Check if file actually exists on disk
            try:
                if os.path.exists(self.banner.path):
                    return self.banner.url
            except (ValueError, AttributeError):
                pass
        # Fallback to original URL if local file doesn't exist
        return self.banner_url or ''

