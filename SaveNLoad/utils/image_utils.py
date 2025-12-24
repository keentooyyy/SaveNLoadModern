"""
Utility functions for image downloading and caching
Handles downloading images from URLs and caching them locally for offline use
"""
import os
import requests
from urllib.parse import urlparse
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def download_image_from_url(image_url, save_path=None, timeout=10):
    """
    Downloads an image from a URL and saves it locally.
    
    Args:
        image_url: URL of the image to download
        save_path: Optional path to save the file (if None, returns file object)
        timeout: Request timeout in seconds
    
    Returns:
        tuple: (success: bool, message: str, file_path or file_object or None)
    """
    if not image_url or not image_url.strip():
        return False, "No image URL provided", None
    
    try:
        # Validate URL
        parsed = urlparse(image_url)
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL format", None
        
        # Download image with timeout and error handling
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(image_url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # Validate content type
        content_type = response.headers.get('Content-Type', '').lower()
        if not content_type.startswith('image/'):
            return False, f"URL does not point to an image (Content-Type: {content_type})", None
        
        # Get file extension from URL or content type
        ext = os.path.splitext(parsed.path)[1] or '.jpg'
        if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            # Try to get extension from content type
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            elif 'png' in content_type:
                ext = '.png'
            elif 'gif' in content_type:
                ext = '.gif'
            elif 'webp' in content_type:
                ext = '.webp'
            else:
                ext = '.jpg'  # Default fallback
        
        # If save_path provided, save directly
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True, "Image downloaded successfully", save_path
        
        # Otherwise, return file object
        temp_file = NamedTemporaryFile(delete=False, suffix=ext)
        for chunk in response.iter_content(chunk_size=8192):
            temp_file.write(chunk)
        temp_file.flush()
        temp_file.seek(0)
        return True, "Image downloaded successfully", temp_file
        
    except requests.exceptions.Timeout:
        return False, "Download timeout - image server did not respond", None
    except requests.exceptions.ConnectionError:
        return False, "Connection error - unable to reach image server (offline?)", None
    except requests.exceptions.RequestException as e:
        return False, f"Failed to download image: {str(e)}", None
    except Exception as e:
        logger.error(f"Error downloading image: {str(e)}", exc_info=True)
        return False, f"Unexpected error: {str(e)}", None


def get_image_url_or_fallback(game):
    """
    Returns the best available image URL for a game.
    Prioritizes local cached file, falls back to original URL.
    
    Args:
        game: Game model instance
    
    Returns:
        str: URL to display (local file URL or original URL)
    """
    # Check if local cached file exists
    if game.banner and game.banner.name:
        try:
            if os.path.exists(game.banner.path):
                return game.banner.url
        except (ValueError, AttributeError):
            pass
    
    # Fallback to original URL
    return game.banner_url or ''

