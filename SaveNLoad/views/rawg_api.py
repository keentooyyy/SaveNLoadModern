import os
import requests
from typing import List, Dict, Optional
from django.conf import settings
from SaveNLoad.utils.api_utils import handle_http_error, handle_request_exception, filter_dlc_games
from SaveNLoad.utils.env_utils import get_env_with_default
from SaveNLoad.utils.api_utils import handle_http_error, handle_request_exception, filter_dlc_games
from SaveNLoad.utils.env_utils import get_env_with_default


def get_popular_games(limit: int = 10) -> List[Dict]:
    """
    Fetch popular games from RAWG API.
    Returns a list of games with title and cover image.
    Requires RAWG API key in RAWG environment variable.
    """
    api_key = get_env_with_default('RAWG')
    
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
        
        # Filter out DLCs
        base_games = filter_dlc_games(data.get('results', []))
        
        for game in base_games:
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
        handle_http_error(e, "RAWG API")
        return []
    except requests.exceptions.RequestException as e:
        handle_request_exception(e, "RAWG API")
        return []
    except Exception as e:
        print(f"Unexpected error in get_popular_games: {e}")
        return []


def search_game(query: str) -> Optional[Dict]:
    """
    Search for a specific game by name.
    Returns the best matching game with title and cover image.
    Requires RAWG API key in RAWG environment variable.
    """
    api_key = get_env_with_default('RAWG')
    
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
        base_games = filter_dlc_games(results)
        for game in base_games:
            image = game.get('background_image')
            if image:  # Only return games with images
                return {
                    'id': game.get('id'),
                    'title': game.get('name', 'Unknown'),
                    'image': image,
                }
        
        return None
    
    except requests.exceptions.HTTPError as e:
        handle_http_error(e, "RAWG API")
        return None
    except requests.exceptions.RequestException as e:
        handle_request_exception(e, "RAWG API")
        return None
    except Exception as e:
        print(f"Unexpected error in search_game: {e}")
        return None


def search_games(query: str, limit: int = 10) -> List[Dict]:
    """
    Search RAWG for multiple games by name.
    Returns a list of base games (no DLCs) with id, title, and image.
    Requires RAWG API key in RAWG environment variable.
    """
    api_key = get_env_with_default('RAWG')
    
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
        
        # Filter out DLCs
        base_games = filter_dlc_games(results)
        
        for game in base_games:
            image = game.get('background_image')
            if not image:
                continue
            
            # Extract release year from released date
            released = game.get('released', '')
            year = ''
            if released:
                try:
                    # Extract year from date string (e.g., "2016-02-26" -> "2016")
                    year = released.split('-')[0] if '-' in released else released[:4] if len(released) >= 4 else ''
                except:
                    year = ''
            
            # Extract all genre names and join them
            # RAWG API returns genres as arrays of objects with 'id', 'name', and 'slug'
            company = ''
            genres = game.get('genres', [])
            
            if genres and len(genres) > 0:
                genre_names = []
                for genre in genres:
                    if isinstance(genre, dict):
                        genre_name = genre.get('name', '')
                        if genre_name:
                            genre_names.append(genre_name)
                
                # Join all genres with comma and space
                if genre_names:
                    company = ', '.join(genre_names)
            
            games.append(
                {
                    'id': game.get('id'),
                    'title': game.get('name', 'Unknown'),
                    'image': image,
                    'year': year,
                    'company': company,
                }
            )
            
            if len(games) >= limit:
                break
        
        return games
    
    except requests.exceptions.HTTPError as e:
        handle_http_error(e, "RAWG API")
        return []
    except requests.exceptions.RequestException as e:
        handle_request_exception(e, "RAWG API")
        return []
    except Exception as e:
        print(f"Unexpected error in search_games: {e}")
        return []

