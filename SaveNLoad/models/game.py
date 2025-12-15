from django.db import models


class Game(models.Model):
    """Game model for managing games and their save file locations"""
    
    name = models.CharField(max_length=255, unique=True)
    banner = models.URLField(max_length=500, blank=True, null=True, help_text="URL to the game banner/image (from RAWG API)")
    save_file_location = models.CharField(max_length=500, help_text="Path to the save file location")
    # Optional timestamp for when this game was last played (for future use in dashboards, sorting, etc.)
    last_played = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'games'
        verbose_name = 'Game'
        verbose_name_plural = 'Games'
        ordering = ['name']
    
    def __str__(self):
        return self.name

