import requests
from typing import List, Dict, Optional
from SaveNLoad.utils.api_utils import handle_http_error, handle_request_exception, filter_dlc_games
from SaveNLoad.utils.env_utils import get_env_with_default

RAWG_BASE_URL = "https://api.rawg.io/api/games"


def _get_rawg_api_key():
    api_key = get_env_with_default('RAWG')
    if not api_key:
        print("RAWG API key not found. Please set the RAWG environment variable.")
        return None
    return api_key


def _fetch_rawg_data(params, context_label):
    try:
        response = requests.get(RAWG_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        handle_http_error(e, context_label)
        return None
    except requests.exceptions.RequestException as e:
        handle_request_exception(e, context_label)
        return None
    except Exception as e:
        print(f"Unexpected error in {context_label}: {e}")
        return None


def get_popular_games(limit: int = 10) -> List[Dict]:
    """
    Fetch popular games from RAWG API.
    Returns a list of games with title and cover image.
    Requires RAWG API key in RAWG environment variable.
    """
    api_key = _get_rawg_api_key()
    if not api_key:
        return []
    
    # Fetch popular games (ordered by rating)
    params = {
        'key': api_key,
        'ordering': '-rating',  # Order by rating descending
        'page_size': limit * 2,  # Fetch more to account for DLC filtering
        'metacritic': '80,100',  # Only highly rated games
        'exclude_additions': 'true'  # Exclude DLCs and expansions
    }
    
    data = _fetch_rawg_data(params, "RAWG API")
    if not data:
        return []
    
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


def search_game(query: str) -> Optional[Dict]:
    """
    Search for a specific game by name.
    Returns the best matching game with title and cover image.
    Requires RAWG API key in RAWG environment variable.
    """
    api_key = _get_rawg_api_key()
    if not api_key:
        return None
    
    params = {
        'key': api_key,
        'search': query,
        'page_size': 10,  # Fetch more to find base game
        'exclude_additions': 'true'  # Exclude DLCs and expansions
    }
    
    data = _fetch_rawg_data(params, "RAWG API")
    if not data:
        return None
    
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


def search_games(query: str, limit: int = 10) -> List[Dict]:
    """
    Search RAWG for multiple games by name.
    Returns a list of base games (no DLCs) with id, title, and image.
    Requires RAWG API key in RAWG environment variable.
    """
    api_key = _get_rawg_api_key()
    if not api_key:
        return []
    
    params = {
        'key': api_key,
        'search': query,
        'page_size': limit * 2,   # fetch extra to account for DLC filtering
        'exclude_additions': 'true',
    }
    
    data = _fetch_rawg_data(params, "RAWG API")
    if not data:
        return []
    
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

