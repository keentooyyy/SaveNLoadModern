"""
Standalone version management utility for client worker build process.

This module provides a self-contained way to get the application version from:
1. GitHub (via raw GitHub URL) - primary source
2. Local version.txt file - fallback for offline development

This is a standalone version (no Django dependencies) for use in build_exe.py
when the full project structure may not be available.
"""
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional


def get_version_from_github(github_url: str, timeout: int = 5) -> Optional[str]:
    """
    Fetch version from GitHub raw URL.
    
    Args:
        github_url: Raw GitHub URL to version.txt (e.g., 
                   'https://raw.githubusercontent.com/username/repo/main/version.txt')
        timeout: Request timeout in seconds (default: 5)
    
    Returns:
        Version string if successful, None if failed
    """
    try:
        with urllib.request.urlopen(github_url, timeout=timeout) as response:
            version = response.read().decode('utf-8').strip()
            # Validate version format (basic check)
            if version and len(version) > 0:
                return version
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        # Print warning message when GitHub fetch fails
        print(f"Warning: Couldn't get version from online ({github_url}): {type(e).__name__}", file=sys.stderr)
    except Exception as e:
        # Any other error - print warning
        print(f"Warning: Couldn't get version from online ({github_url}): {type(e).__name__}", file=sys.stderr)
    return None


def get_version_from_local(version_file_path: Path) -> Optional[str]:
    """
    Read version from local version.txt file.
    
    Args:
        version_file_path: Path to version.txt file
    
    Returns:
        Version string if file exists and is readable, None otherwise
    """
    try:
        if version_file_path.exists():
            version = version_file_path.read_text(encoding='utf-8').strip()
            if version and len(version) > 0:
                return version
        else:
            print(f"Warning: Local version file not found: {version_file_path}", file=sys.stderr)
    except Exception as e:
        # File exists but can't be read
        print(f"Warning: Couldn't read local version file ({version_file_path}): {type(e).__name__}", file=sys.stderr)
    return None


def get_app_version(
    base_dir: Optional[Path] = None,
    github_url: Optional[str] = None
) -> str:
    """
    Get application version from GitHub or local file.
    
    Priority:
    1. GitHub URL (if provided and accessible)
    2. Local version.txt file (checks parent directory first, then current directory)
    3. Error message indicating version couldn't be retrieved (fallback)
    
    Args:
        base_dir: Base directory to search for version.txt. If None, uses script directory's parent.
        github_url: Optional GitHub raw URL to version.txt. If None, will try
                   to get from VERSION_GITHUB_URL environment variable.
                   Format: 'https://raw.githubusercontent.com/username/repo/branch/version.txt'
    
    Returns:
        Version string (semantic version format, e.g., '1.0.0') or error message
    """
    # Determine base directory - use script location if not provided
    if base_dir is None:
        # Get the directory where this script is located
        script_dir = Path(__file__).parent.absolute()
        # Look in parent directory (project root) first, then current directory
        base_dir = script_dir.parent
    
    # Try to get GitHub URL from environment variable if not provided
    if github_url is None:
        github_url = os.getenv('VERSION_GITHUB_URL')
    
    # Try GitHub first (if URL is provided)
    if github_url:
        version = get_version_from_github(github_url)
        if version:
            return version
    
    # Fall back to local file - check parent directory first (project root)
    version_file_path = base_dir / 'version.txt'
    version = get_version_from_local(version_file_path)
    if version:
        return version
    
    # Also check current directory (client_worker folder) as fallback
    script_dir = Path(__file__).parent.absolute()
    local_version_path = script_dir / 'version.txt'
    if local_version_path != version_file_path:
        version = get_version_from_local(local_version_path)
        if version:
            return version
    
    # Final fallback - couldn't get version from any source
    error_msg = "couldn't get version from online"
    print(f"Error: {error_msg} - using fallback version indicator", file=sys.stderr)
    return error_msg

