"""
Client Worker for SaveNLoad
This script runs on client PCs and handles save/load operations
"""
import os
import sys
import json
import requests
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from ftp_client import FTPClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class SaveNLoadClient:
    """Client worker for SaveNLoad application"""
    
    def __init__(self, server_url: str, session_cookie: str = None):
        """
        Initialize client worker
        
        Args:
            server_url: Base URL of the Django server (e.g., 'http://192.168.88.101:8000')
            session_cookie: Optional session cookie for authentication
        """
        self.server_url = server_url.rstrip('/')
        self.session = requests.Session()
        
        # Setup FTP client
        ftp_host = os.getenv('FTP_HOST')
        ftp_port = int(os.getenv('FTP_PORT', '21'))
        ftp_username = os.getenv('FTP_USERNAME')
        ftp_password = os.getenv('FTP_PASSWORD')
        
        if not all([ftp_host, ftp_username, ftp_password]):
            raise ValueError("FTP credentials must be set in environment variables")
        
        self.ftp_client = FTPClient(
            host=ftp_host,
            port=ftp_port,
            username=ftp_username,
            password=ftp_password
        )
        
        # Set session cookie if provided
        if session_cookie:
            self.session.cookies.set('sessionid', session_cookie)
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, 
                     json_data: Dict = None) -> Dict[str, Any]:
        """Make HTTP request to Django server"""
        url = f"{self.server_url}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=data)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=json_data or data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise
    
    def save_game(self, game_id: int, local_save_path: str, 
                 username: str, game_name: str) -> Dict[str, Any]:
        """
        Save game - backup from local PC to FTP
        
        Args:
            game_id: Game ID from Django server
            local_save_path: Path to local save file or directory
            username: Username for FTP organization
            game_name: Game name for FTP organization
        
        Returns:
            Dict with success status and message
        """
        logger.info(f"Saving game {game_id} from {local_save_path}")
        
        if not os.path.exists(local_save_path):
            return {
                'success': False,
                'error': f'Local save path does not exist: {local_save_path}'
            }
        
        try:
            # If it's a directory, upload all files
            # If it's a file, upload just that file
            if os.path.isdir(local_save_path):
                uploaded_files = []
                failed_files = []
                
                for root, dirs, files in os.walk(local_save_path):
                    for filename in files:
                        local_file = os.path.join(root, filename)
                        rel_path = os.path.relpath(local_file, local_save_path)
                        remote_filename = rel_path.replace('\\', '/')
                        
                        success, message = self.ftp_client.upload_save(
                            username=username,
                            game_name=game_name,
                            local_file_path=local_file,
                            remote_filename=remote_filename
                        )
                        
                        if success:
                            uploaded_files.append(remote_filename)
                            logger.info(f"Uploaded: {remote_filename}")
                        else:
                            failed_files.append({'file': remote_filename, 'error': message})
                            logger.error(f"Failed to upload {remote_filename}: {message}")
                
                if failed_files:
                    return {
                        'success': False,
                        'message': f'Uploaded {len(uploaded_files)} file(s), {len(failed_files)} failed',
                        'uploaded_files': uploaded_files,
                        'failed_files': failed_files
                    }
                
                return {
                    'success': True,
                    'message': f'Successfully uploaded {len(uploaded_files)} file(s)',
                    'uploaded_files': uploaded_files
                }
            else:
                # Single file upload
                success, message = self.ftp_client.upload_save(
                    username=username,
                    game_name=game_name,
                    local_file_path=local_save_path
                )
                
                if success:
                    logger.info(f"Successfully saved: {message}")
                    return {'success': True, 'message': message}
                else:
                    logger.error(f"Save failed: {message}")
                    return {'success': False, 'error': message}
                    
        except Exception as e:
            logger.error(f"Save operation failed: {e}")
            return {'success': False, 'error': f'Save operation failed: {str(e)}'}
    
    def load_game(self, game_id: int, local_save_path: str,
                 username: str, game_name: str, save_folder_number: Optional[int] = None) -> Dict[str, Any]:
        """
        Load game - download from FTP to local PC
        
        Args:
            game_id: Game ID from Django server
            local_save_path: Path where to save files locally
            username: Username for FTP organization
            game_name: Game name for FTP organization
            save_folder_number: Optional specific save folder number
        
        Returns:
            Dict with success status and message
        """
        logger.info(f"Loading game {game_id} to {local_save_path}")
        
        try:
            # List all files in the save folder
            success, files, message = self.ftp_client.list_saves(
                username=username,
                game_name=game_name,
                save_folder_number=save_folder_number
            )
            
            if not success or not files:
                return {
                    'success': False,
                    'error': f'No save files found: {message}'
                }
            
            # Download all files
            downloaded_files = []
            failed_files = []
            
            # Ensure local directory exists
            if os.path.isdir(local_save_path) or not os.path.exists(local_save_path):
                os.makedirs(local_save_path, exist_ok=True)
            
            for file_info in files:
                remote_filename = file_info['name']
                
                if os.path.isdir(local_save_path):
                    local_file = os.path.join(local_save_path, remote_filename)
                    if '/' in remote_filename:
                        nested_dir = os.path.join(local_save_path, os.path.dirname(remote_filename))
                        os.makedirs(nested_dir, exist_ok=True)
                else:
                    local_file = local_save_path
                
                success, message = self.ftp_client.download_save(
                    username=username,
                    game_name=game_name,
                    remote_filename=remote_filename,
                    local_file_path=local_file,
                    save_folder_number=save_folder_number
                )
                
                if success:
                    downloaded_files.append(remote_filename)
                    logger.info(f"Downloaded: {remote_filename}")
                else:
                    failed_files.append({'file': remote_filename, 'error': message})
                    logger.error(f"Failed to download {remote_filename}: {message}")
            
            if failed_files:
                return {
                    'success': False,
                    'message': f'Downloaded {len(downloaded_files)} file(s), {len(failed_files)} failed',
                    'downloaded_files': downloaded_files,
                    'failed_files': failed_files
                }
            
            logger.info(f"Successfully loaded {len(downloaded_files)} file(s)")
            return {
                'success': True,
                'message': f'Successfully downloaded {len(downloaded_files)} file(s)',
                'downloaded_files': downloaded_files
            }
                    
        except Exception as e:
            logger.error(f"Load operation failed: {e}")
            return {'success': False, 'error': f'Load operation failed: {str(e)}'}
    
    def get_game_info(self, game_id: int) -> Dict[str, Any]:
        """Get game information from Django server"""
        try:
            return self._make_request('GET', f'/admin/games/{game_id}/')
        except Exception as e:
            logger.error(f"Failed to get game info: {e}")
            return {'error': str(e)}


def main():
    """Main entry point for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SaveNLoad Client Worker')
    parser.add_argument('--server', required=True, help='Django server URL (e.g., http://192.168.88.101:8000)')
    parser.add_argument('--game-id', type=int, required=True, help='Game ID')
    parser.add_argument('--username', required=True, help='Username')
    parser.add_argument('--action', choices=['save', 'load'], required=True, help='Action to perform')
    parser.add_argument('--local-path', required=True, help='Local save file/directory path')
    parser.add_argument('--session', help='Session cookie for authentication (optional)')
    parser.add_argument('--save-folder', type=int, help='Specific save folder number (optional)')
    
    args = parser.parse_args()
    
    try:
        client = SaveNLoadClient(args.server, args.session)
        
        # Get game info
        game_info = client.get_game_info(args.game_id)
        if 'error' in game_info:
            print(f"Error: {game_info['error']}")
            sys.exit(1)
        
        game_name = game_info.get('name', 'Unknown')
        
        if args.action == 'save':
            result = client.save_game(
                game_id=args.game_id,
                local_save_path=args.local_path,
                username=args.username,
                game_name=game_name
            )
        else:  # load
            result = client.load_game(
                game_id=args.game_id,
                local_save_path=args.local_path,
                username=args.username,
                game_name=game_name,
                save_folder_number=args.save_folder
            )
        
        if result.get('success'):
            print(f"Success: {result.get('message')}")
            sys.exit(0)
        else:
            print(f"Error: {result.get('error', result.get('message', 'Unknown error'))}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Client worker failed: {e}")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

