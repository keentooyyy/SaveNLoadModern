"""
API and HTTP utilities
Common patterns for API requests and error handling
"""
import requests
from typing import Dict, List, Optional


def handle_http_error(e: requests.exceptions.HTTPError, api_name: str = "API") -> None:
    """
    Handle HTTP errors from API requests with helpful messages
    
    Used in:
    - RAWG API error handling
    - Any external API calls
    
    Args:
        e: HTTPError exception
        api_name: Name of the API (for error messages)

    Returns:
        None
    """
    if hasattr(e, 'response') and e.response is not None:
        if e.response.status_code == 401:
            print(f"{api_name}: Unauthorized - Invalid or missing API key. Please check your API key.")
        else:
            print(f"Error fetching from {api_name}: {e}")
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text[:200]}")


def handle_request_exception(e: Exception, api_name: str = "API") -> None:
    """
    Handle general request exceptions
    
    Used in:
    - RAWG API error handling
    - Network error handling
    
    Args:
        e: Exception
        api_name: Name of the API

    Returns:
        None
    """
    print(f"Error fetching from {api_name}: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"Response status: {e.response.status_code}")
        print(f"Response body: {e.response.text[:200]}")


def filter_dlc_games(games: List[Dict]) -> List[Dict]:
    """
    Filter out DLCs and addons from game list
    
    Used in:
    - RAWG API results
    - Any game list that needs DLC filtering
    
    Args:
        games: List of game dicts from API
        
    Returns:
        Filtered list (only base games)
    """
    return [
        game for game in games
        if not (game.get('parent_game') or game.get('is_addon', False))
    ]

