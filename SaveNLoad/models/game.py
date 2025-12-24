from django.db import models
import os


class Game(models.Model):
    """Game model for managing games and their save file locations"""
    
    name = models.CharField(max_length=255, unique=True)
    # Store cached local image file
    banner = models.ImageField(upload_to='game_banners/', blank=True, null=True, help_text="Cached local banner image file")
    # Keep original URL for reference and re-download if needed
    banner_url = models.URLField(max_length=500, blank=True, null=True, help_text="Original URL to the game banner/image (from RAWG API)")
    save_file_locations = models.JSONField(
        default=list,
        help_text="List of save file location paths (array of strings)"
    )
    # Mapping of local save paths to path_index on FTP server
    # Format: {"C:\\path1": 1, "C:\\path2": 2}
    # This ensures each local path always maps to the same path_X folder on the server
    path_mappings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Mapping of local save path to path_index (1,2,3...). e.g., {'C:\\\\path1': 1, 'C:\\\\path2': 2}"
    )
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
    
    def get_path_index(self, local_path: str) -> int:
        """
        Get the path_index for a local path.
        If mapping doesn't exist, creates a new one.
        
        Args:
            local_path: Local save file path
            
        Returns:
            path_index (1-based) for this path
        """
        if not self.path_mappings:
            self.path_mappings = {}
        
        # Normalize path for consistent mapping (handle both / and \)
        normalized_path = os.path.normpath(local_path)
        
        # Check if path already has a mapping
        if normalized_path in self.path_mappings:
            return self.path_mappings[normalized_path]
        
        # Find next available path_index
        existing_indices = set(self.path_mappings.values()) if self.path_mappings else set()
        next_index = 1
        while next_index in existing_indices:
            next_index += 1
        
        # Create new mapping
        self.path_mappings[normalized_path] = next_index
        self.save(update_fields=['path_mappings', 'updated_at'])
        
        return next_index
    
    def get_path_index_or_none(self, local_path: str) -> int:
        """
        Get the path_index for a local path, or None if not mapped.
        Does not create new mappings.
        
        Args:
            local_path: Local save file path
            
        Returns:
            path_index (1-based) or None if not found
        """
        if not self.path_mappings:
            return None
        
        normalized_path = os.path.normpath(local_path)
        return self.path_mappings.get(normalized_path)
    
    def cleanup_path_mappings(self):
        """
        Remove mappings for paths that are no longer in save_file_locations.
        Call this when save_file_locations is updated.
        """
        if not self.path_mappings:
            return
        
        # Get normalized current paths
        current_paths = {os.path.normpath(path) for path in self.save_file_locations if path}
        
        # Remove mappings for paths not in current list
        paths_to_remove = [path for path in self.path_mappings.keys() if path not in current_paths]
        
        if paths_to_remove:
            for path in paths_to_remove:
                del self.path_mappings[path]
            self.save(update_fields=['path_mappings', 'updated_at'])

