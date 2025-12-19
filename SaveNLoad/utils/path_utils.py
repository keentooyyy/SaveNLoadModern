"""
Path and name sanitization utilities
Reusable across models, views, and client worker
"""
import re


def sanitize_game_name(game_name: str) -> str:
    """
    Sanitize game name for use in file paths
    Removes special characters, keeps alphanumeric, spaces, hyphens, underscores
    Replaces spaces with underscores
    
    Used in:
    - SaveFolder._generate_remote_path
    - Game deletion operations
    - Client worker path generation
    
    Args:
        game_name: Raw game name
        
    Returns:
        Sanitized game name safe for file paths
    """
    if not game_name:
        return ""
    
    # Keep only alphanumeric, spaces, hyphens, underscores
    safe_name = "".join(c for c in game_name if c.isalnum() or c in (' ', '-', '_')).strip()
    # Replace spaces with underscores
    safe_name = safe_name.replace(' ', '_')
    
    return safe_name


def generate_save_folder_path(username: str, game_name: str, folder_number: int) -> str:
    """
    Generate full remote path for a save folder in FTP format (forward slashes)
    
    Used in:
    - SaveFolder._generate_remote_path
    - Client worker operations
    
    Args:
        username: User's username
        game_name: Game name (will be sanitized)
        folder_number: Save folder number (1-10)
        
    Returns:
        Full path in format: username/gamename/save_N
    """
    safe_game_name = sanitize_game_name(game_name)
    return f"{username}/{safe_game_name}/save_{folder_number}"


def generate_game_directory_path(username: str, game_name: str) -> str:
    """
    Generate game directory path (without save folder number)
    
    Used in:
    - Game deletion operations (deletes entire game directory)
    
    Args:
        username: User's username
        game_name: Game name (will be sanitized)
        
    Returns:
        Game directory path in format: username/gamename
    """
    safe_game_name = sanitize_game_name(game_name)
    return f"{username}/{safe_game_name}"


def normalize_path_separators(path: str) -> str:
    """
    Normalize path separators to forward slashes (FTP format)
    Removes leading/trailing slashes
    
    Used in:
    - Client worker path handling
    - Remote path building
    
    Args:
        path: Path with mixed or Windows separators
        
    Returns:
        Normalized path with forward slashes
    """
    if not path:
        return ""
    
    # Replace backslashes with forward slashes
    path = path.replace('\\', '/')
    # Remove leading/trailing slashes
    path = path.strip('/')
    
    return path


def build_rclone_remote_path(remote_name: str, path: str) -> str:
    """
    Build rclone remote path string (e.g., "ftp:/path/to/file")
    
    Used in:
    - RcloneClient._build_remote_path
    - All rclone operations
    
    Args:
        remote_name: Remote name (e.g., 'ftp')
        path: Path to append (will be normalized)
        
    Returns:
        Full rclone remote path
    """
    path = normalize_path_separators(path)
    if path:
        return f"{remote_name}:/{path}"
    else:
        return f"{remote_name}:/"

