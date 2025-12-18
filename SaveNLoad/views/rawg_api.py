import os
import requests
from typing import List, Dict, Optional
from django.conf import settings


def get_popular_games(limit: int = 10) -> List[Dict]:
    """
    Fetch popular games from RAWG API.
    Returns a list of games with title and cover image.
    Requires RAWG API key in RAWG environment variable.
    """
    api_key = os.getenv('RAWG')
    
    if not api_key:
        print("RAWG API key not found. Please set the RAWG environment variable.")
        return []
    
    try:
        # Fetch popular games (ordered by rating)
        url = f"https://api.rawg.io/api/games"
        params = {
            'key': api_key,
            'ordering': '-rating',  # Order by rating descending
            'page_size': limit * 2,  # Fetch more to account for DLC filtering
            'metacritic': '80,100',  # Only highly rated games
            'exclude_additions': 'true'  # Exclude DLCs and expansions
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        games = []
        
        for game in data.get('results', []):
            # Skip DLCs - check if it's a DLC (has parent_game or is_addon)
            if game.get('parent_game') or game.get('is_addon', False):
                continue
            
            # Only include games that have an image
            image = game.get('background_image')
            if image:  # Only add games with images
                games.append({
                    'title': game.get('name', 'Unknown'),
                    'image': image,
                })
                
                # Stop when we have enough base games
                if len(games) >= limit:
                    break
        
        return games
    
    except requests.exceptions.HTTPError as e:
        if hasattr(e, 'response') and e.response is not None:
            if e.response.status_code == 401:
                print("RAWG API: Unauthorized - Invalid or missing API key. Please check your RAWG environment variable.")
            else:
                print(f"Error fetching games from RAWG API: {e}")
                print(f"Response status: {e.response.status_code}")
                print(f"Response body: {e.response.text[:200]}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching games from RAWG API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text[:200]}")
        return []
    except Exception as e:
        print(f"Unexpected error in get_popular_games: {e}")
        import traceback
        traceback.print_exc()
        return []


def search_game(query: str) -> Optional[Dict]:
    """
    Search for a specific game by name.
    Returns the best matching game with title and cover image.
    Requires RAWG API key in RAWG environment variable.
    """
    api_key = os.getenv('RAWG')
    
    if not api_key:
        print("RAWG API key not found. Please set the RAWG environment variable.")
        return None
    
    try:
        url = f"https://api.rawg.io/api/games"
        params = {
            'key': api_key,
            'search': query,
            'page_size': 10,  # Fetch more to find base game
            'exclude_additions': 'true'  # Exclude DLCs and expansions
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        results = data.get('results', [])
        
        # Find the first base game (not a DLC)
        for game in results:
            # Skip DLCs - check if it's a DLC (has parent_game or is_addon)
            if game.get('parent_game') or game.get('is_addon', False):
                continue
            
            image = game.get('background_image')
            if image:  # Only return games with images
                return {
                    'id': game.get('id'),
                    'title': game.get('name', 'Unknown'),
                    'image': image,
                }
        
        return None
    
    except requests.exceptions.HTTPError as e:
        if hasattr(e, 'response') and e.response is not None:
            if e.response.status_code == 401:
                print("RAWG API: Unauthorized - Invalid or missing API key. Please check your RAWG environment variable.")
            else:
                print(f"Error searching game in RAWG API: {e}")
                print(f"Response status: {e.response.status_code}")
                print(f"Response body: {e.response.text[:200]}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error searching game in RAWG API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text[:200]}")
        return None
    except Exception as e:
        print(f"Unexpected error in search_game: {e}")
        import traceback
        traceback.print_exc()
        return None


def search_games(query: str, limit: int = 10) -> List[Dict]:
    """
    Search RAWG for multiple games by name.
    Returns a list of base games (no DLCs) with id, title, and image.
    Requires RAWG API key in RAWG environment variable.
    """
    api_key = os.getenv('RAWG')
    
    if not api_key:
        print("RAWG API key not found. Please set the RAWG environment variable.")
        return []
    
    try:
        url = "https://api.rawg.io/api/games"
        params = {
            'key': api_key,
            'search': query,
            'page_size': limit * 2,   # fetch extra to account for DLC filtering
            'exclude_additions': 'true',
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        results = data.get('results', [])
        
        games: List[Dict] = []
        
        for game in results:
            # Skip DLCs and addons
            if game.get('parent_game') or game.get('is_addon', False):
                continue
            
            image = game.get('background_image')
            if not image:
                continue
            
            games.append(
                {
                    'id': game.get('id'),
                    'title': game.get('name', 'Unknown'),
                    'image': image,
                }
            )
            
            if len(games) >= limit:
                break
        
        return games
    
    except requests.exceptions.HTTPError as e:
        if hasattr(e, 'response') and e.response is not None:
            if e.response.status_code == 401:
                print("RAWG API: Unauthorized - Invalid or missing API key. Please check your RAWG environment variable.")
            else:
                print(f"Error searching games in RAWG API: {e}")
                print(f"Response status: {e.response.status_code}")
                print(f"Response body: {e.response.text[:200]}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error searching games in RAWG API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text[:200]}")
        return []
    except Exception as e:
        print(f"Unexpected error in search_games: {e}")
        import traceback
        traceback.print_exc()
        return []

