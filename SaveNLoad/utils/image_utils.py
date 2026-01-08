"""
Utility functions for image downloading and caching
Handles downloading images from URLs and caching them locally for offline use
"""
import os
import re
import requests
from urllib.parse import urlparse
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.conf import settings


def is_local_url(image_url, request=None):
    """
    Check if image URL is from the same server (localhost, 127.0.0.1, or server IP).
    Skips download for local URLs.
    
    Args:
        image_url: URL to check
        request: Optional Django request object to get server host
        
    Returns:
        bool: True if URL is from same server, False otherwise
    """
    if not image_url:
        return False
    
    try:
        parsed = urlparse(image_url)
        url_host = parsed.netloc.split(':')[0]  # Remove port if present
        
        # Check common localhost patterns
        localhost_patterns = [
            'localhost',
            '127.0.0.1',
            '0.0.0.0',
            '::1',  # IPv6 localhost
        ]
        
        # Check if URL host is localhost
        if url_host.lower() in localhost_patterns:
            return True
        
        # Check if URL matches server host (if request provided)
        if request:
            server_host = request.get_host().split(':')[0]  # Remove port
            if url_host == server_host:
                return True
            
            # Also check against HTTP_HOST header
            http_host = request.META.get('HTTP_HOST', '').split(':')[0]
            if url_host == http_host:
                return True
        
        # Check if URL is a local IP (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
        # and matches server IP if available
        local_ip_pattern = re.compile(r'^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)')
        if local_ip_pattern.match(url_host):
            if request:
                # Try to get server IP from request
                server_host = request.get_host().split(':')[0]
                if url_host == server_host:
                    return True
        
        return False
    except Exception:
        return False


def download_image_from_url(image_url, save_path=None, timeout=3, max_bytes=5 * 1024 * 1024):
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
        
        # Validate content length (prevent large downloads)
        content_length = response.headers.get('Content-Length')
        if content_length:
            try:
                if int(content_length) > max_bytes:
                    return False, "Image is too large", None
            except ValueError:
                pass

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
                total = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > max_bytes:
                        return False, "Image is too large", None
                    f.write(chunk)
            return True, "Image downloaded successfully", save_path
        
        # Otherwise, return file object
        temp_file = NamedTemporaryFile(delete=False, suffix=ext)
        total = 0
        for chunk in response.iter_content(chunk_size=8192):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                return False, "Image is too large", None
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
        print(f"ERROR: Error downloading image: {str(e)}")
        return False, f"Unexpected error: {str(e)}", None


def get_image_url_or_fallback(game, request=None):
    """
    Returns the best available image URL for a game.
    Prioritizes local cached file (faster, works offline), falls back to original URL.
    Converts relative URLs to absolute URLs if request is provided.
    
    Performance optimized: Removed expensive os.path.exists() check.
    Local cached files are checked first for better performance and offline support.
    
    Args:
        game: Game model instance
        request: Optional Django request object for building absolute URLs
    
    Returns:
        str: URL to display (absolute URL if request provided, otherwise relative or original URL)
    """
    # Prioritize local cached file first (faster, works offline)
    # Files exist in media/game_banners/ - use them when available
    if game.banner and game.banner.name:
        try:
            # Access the URL property - Django generates this from MEDIA_URL + file path
            # This doesn't check if file exists, just generates the URL
            url = game.banner.url
            # Only use banner.url if it's a valid non-empty URL
            if url and url.strip() and url != '/':
                # Convert relative URL to absolute if request is provided
                if request and url.startswith('/'):
                    return request.build_absolute_uri(url)
                return url
        except (ValueError, AttributeError, OSError) as e:
            # File doesn't exist or other error - fall through to banner_url
            # Log for debugging but don't fail
            print(f"DEBUG: Failed to get banner.url for game {game.id}: {e}")
            pass
    # Fallback to original URL (should already be absolute)
    # This is used when local cached file doesn't exist or fails
    if game.banner_url:
        return game.banner_url
    
    # No banner available
    return ''
    
    # Fallback to original URL (should already be absolute)
    # This is used when local cached file doesn't exist or fails
    if game.banner_url:
        return game.banner_url
    
    # No banner available
    return ''

