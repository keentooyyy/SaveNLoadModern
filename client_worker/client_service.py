"""
Client Worker Service
Runs on client PC to handle save/load operations with proper permissions
"""
import os
import sys
import json
import time
import requests
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from ftp_client import FTPClient

# Setup logging
log_dir = Path.home() / '.savenload' / 'logs'
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'client_worker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class ClientWorkerService:
    """Service that runs on client PC to handle save/load operations"""
    
    def __init__(self, server_url: str, poll_interval: int = 5):
        """
        Initialize client worker service
        
        Args:
            server_url: Base URL of the Django server
            poll_interval: How often to poll for pending operations (seconds)
        """
        # Add http:// scheme if missing
        if not server_url.startswith(('http://', 'https://')):
            server_url = f'http://{server_url}'
        # Add default port if no port specified
        if '://' in server_url:
            scheme, rest = server_url.split('://', 1)
            if ':' not in rest.split('/')[0]:  # No port in hostname
                # Default to port 8000 for Django
                host = rest.split('/')[0]
                path = rest[len(host):] if len(rest) > len(host) else ''
                server_url = f'{scheme}://{host}:8000{path}'
        self.server_url = server_url.rstrip('/')
        self.poll_interval = poll_interval
        self.session = requests.Session()
        self.running = False
        
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
        
        logger.info("Client Worker Service initialized")
    
    def check_permissions(self) -> bool:
        """Check if we have necessary permissions to access files"""
        try:
            # Try to access user's Documents folder (common save location)
            test_path = Path.home() / 'Documents'
            if test_path.exists():
                test_path.stat()  # This will raise if no permission
            return True
        except PermissionError:
            logger.warning("Insufficient permissions to access files")
            return False
    
    
    def save_game(self, game_id: int, local_save_path: str, 
                 username: str, game_name: str, save_folder_number: int) -> Dict[str, Any]:
        """Save game - backup from local PC to FTP"""
        logger.info(f"Saving game {game_id} from {local_save_path} to save_folder {save_folder_number}")
        
        if not os.path.exists(local_save_path):
            return {
                'success': False,
                'error': f'Local save path does not exist: {local_save_path}'
            }
        
        try:
            if os.path.isdir(local_save_path):
                uploaded_files = []
                failed_files = []
                
                # Collect all files first
                file_list = []
                for root, dirs, files in os.walk(local_save_path):
                    for filename in files:
                        local_file = os.path.join(root, filename)
                        rel_path = os.path.relpath(local_file, local_save_path)
                        remote_filename = rel_path.replace('\\', '/')
                        file_list.append((local_file, remote_filename))
                
                file_count = len(file_list)
                logger.info(f"Found {file_count} file(s) in {local_save_path}")
                
                if file_count == 0:
                    logger.warning(f"No files found in directory: {local_save_path}")
                    return {
                        'success': False,
                        'error': f'No files found in directory: {local_save_path}'
                    }
                
                # Process files in parallel batches (max 50 at a time)
                MAX_WORKERS = min(50, file_count)
                logger.info(f"Processing {file_count} file(s) with {MAX_WORKERS} parallel workers")
                
                def upload_file(file_info: Tuple[str, str]) -> Tuple[bool, str, str]:
                    """Upload a single file - returns (success, remote_filename, message)"""
                    local_file, remote_filename = file_info
                    try:
                        success, message = self.ftp_client.upload_save(
                            username=username,
                            game_name=game_name,
                            local_file_path=local_file,
                            folder_number=save_folder_number,
                            remote_filename=remote_filename
                        )
                        return (success, remote_filename, message)
                    except Exception as e:
                        logger.error(f"Exception uploading {remote_filename}: {e}")
                        return (False, remote_filename, str(e))
                
                # Process files in parallel
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    future_to_file = {executor.submit(upload_file, file_info): file_info[1] 
                                     for file_info in file_list}
                    
                    for future in as_completed(future_to_file):
                        remote_filename = future_to_file[future]
                        try:
                            success, remote_filename, message = future.result()
                            if success:
                                uploaded_files.append(remote_filename)
                                logger.info(f"Uploaded: {remote_filename}")
                            else:
                                failed_files.append({'file': remote_filename, 'error': message})
                                logger.error(f"Failed to upload {remote_filename}: {message}")
                        except Exception as e:
                            failed_files.append({'file': remote_filename, 'error': str(e)})
                            logger.error(f"Exception processing {remote_filename}: {e}")
                
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
                success, message = self.ftp_client.upload_save(
                    username=username,
                    game_name=game_name,
                    local_file_path=local_save_path,
                    folder_number=save_folder_number
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
                 username: str, game_name: str, save_folder_number: int) -> Dict[str, Any]:
        """Load game - download from FTP to local PC"""
        logger.info(f"Loading game {game_id} to {local_save_path} from save_folder {save_folder_number}")
        
        try:
            success, files, message = self.ftp_client.list_saves(
                username=username,
                game_name=game_name,
                folder_number=save_folder_number
            )
            
            logger.info(f"List saves result: success={success}, files_count={len(files) if files else 0}, message={message}")
            
            if not success:
                logger.error(f"Failed to list saves: {message}")
                return {
                    'success': False,
                    'error': f'Failed to list saves: {message}'
                }
            
            if not files:
                logger.warning(f"No save files found: {message}")
                return {
                    'success': False,
                    'error': f'No save files found: {message}'
                }
            
            downloaded_files = []
            failed_files = []
            
            # Ensure the local save path exists as a directory
            # Always treat it as a directory for loading (we download multiple files)
            if not os.path.exists(local_save_path):
                os.makedirs(local_save_path, exist_ok=True)
                logger.info(f"Created directory: {local_save_path}")
            elif os.path.isfile(local_save_path):
                # If it's a file, use its parent directory instead
                local_save_path = os.path.dirname(local_save_path)
                os.makedirs(local_save_path, exist_ok=True)
                logger.info(f"Path was a file, using parent directory: {local_save_path}")
            
            if not os.path.isdir(local_save_path):
                return {
                    'success': False,
                    'error': f'Local save path is not a directory: {local_save_path}'
                }
            
            logger.info(f"Downloading {len(files)} file(s) to directory: {local_save_path}")
            
            # Prepare file list and create directories first
            file_list = []
            for file_info in files:
                remote_filename = file_info['name']
                
                # Always treat local_save_path as a directory for downloads
                # Handle nested paths (subdirectories in the save)
                if '/' in remote_filename or '\\' in remote_filename:
                    # Normalize path separators to use forward slashes
                    remote_filename_normalized = remote_filename.replace('\\', '/')
                    # Create nested directory structure
                    nested_dir = os.path.join(local_save_path, os.path.dirname(remote_filename_normalized))
                    os.makedirs(nested_dir, exist_ok=True)
                    # Build local file path using OS-specific separators
                    local_file = os.path.join(local_save_path, *remote_filename_normalized.split('/'))
                else:
                    # Simple filename, no subdirectories
                    local_file = os.path.join(local_save_path, remote_filename)
                
                file_list.append((remote_filename, local_file))
            
            # Process files in parallel batches (max 50 at a time)
            MAX_WORKERS = min(50, len(file_list))
            logger.info(f"Processing {len(file_list)} file(s) with {MAX_WORKERS} parallel workers")
            
            def download_file(file_info: Tuple[str, str]) -> Tuple[bool, str, str]:
                """Download a single file - returns (success, remote_filename, message)"""
                remote_filename, local_file = file_info
                try:
                    success, message = self.ftp_client.download_save(
                        username=username,
                        game_name=game_name,
                        remote_filename=remote_filename,
                        local_file_path=local_file,
                        folder_number=save_folder_number
                    )
                    return (success, remote_filename, message)
                except Exception as e:
                    logger.error(f"Exception downloading {remote_filename}: {e}")
                    return (False, remote_filename, str(e))
            
            # Process files in parallel
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_file = {executor.submit(download_file, file_info): file_info[0] 
                                 for file_info in file_list}
                
                for future in as_completed(future_to_file):
                    remote_filename = future_to_file[future]
                    try:
                        success, remote_filename, message = future.result()
                        if success:
                            downloaded_files.append(remote_filename)
                            logger.info(f"Downloaded: {remote_filename}")
                        else:
                            failed_files.append({'file': remote_filename, 'error': message})
                            logger.error(f"Failed to download {remote_filename}: {message}")
                    except Exception as e:
                        failed_files.append({'file': remote_filename, 'error': str(e)})
                        logger.error(f"Exception processing {remote_filename}: {e}")
            
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
    
    def register_with_server(self, client_id: str) -> bool:
        """Register this client with the Django server"""
        try:
            response = self.session.post(
                f"{self.server_url}/api/client/register/",
                json={'client_id': client_id}
            )
            if response.status_code == 200:
                logger.info(f"Successfully registered with server as {client_id}")
                return True
            else:
                logger.error(f"Registration failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to register with server: {e}")
            return False
    
    def send_heartbeat(self, client_id: str) -> bool:
        """Send heartbeat to Django server"""
        try:
            response = self.session.post(
                f"{self.server_url}/api/client/heartbeat/",
                json={'client_id': client_id}
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send heartbeat: {e}")
            return False
    
    def unregister_from_server(self, client_id: str) -> bool:
        """Unregister this client from the Django server (called on shutdown)"""
        try:
            response = self.session.post(
                f"{self.server_url}/api/client/unregister/",
                json={'client_id': client_id}
            )
            if response.status_code == 200:
                logger.info(f"Successfully unregistered from server: {client_id}")
                return True
            else:
                logger.warning(f"Unregistration failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to unregister from server: {e}")
            return False
    
    def run(self):
        """Run the service (polling mode)"""
        logger.info("Starting Client Worker Service...")
        
        # Check permissions
        if not self.check_permissions():
            logger.warning("Insufficient permissions. You may need to run with elevated privileges.")
        
        self.running = True
        
        # Generate unique client ID based on PC information
        # This ensures each PC has a unique identifier
        import platform
        import uuid
        
        # Try to get a unique identifier for this PC
        # Use MAC address + hostname for uniqueness
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                           for elements in range(0,2*6,2)][::-1])
            hostname = platform.node() or platform.uname().node
            client_id = f"{hostname}_{mac}"
        except:
            # Fallback to hostname + machine ID if MAC address unavailable
            hostname = platform.node() or platform.uname().node or 'unknown'
            try:
                # Try to get machine ID (Linux) or use hostname + system info
                if sys.platform == 'linux':
                    import subprocess
                    machine_id = subprocess.check_output(['cat', '/etc/machine-id']).decode().strip()[:8]
                    client_id = f"{hostname}_{machine_id}"
                else:
                    # Windows/Mac fallback
                    machine_info = platform.machine() + platform.processor()
                    client_id = f"{hostname}_{hash(machine_info) & 0xffffffff:08x}"
            except:
                # Last resort: hostname + random UUID (stored for persistence)
                # Store in a file so it's consistent across runs
                client_id_file = Path.home() / '.savenload' / 'client_id.txt'
                if client_id_file.exists():
                    client_id = client_id_file.read_text().strip()
                else:
                    client_id = f"{hostname}_{uuid.uuid4().hex[:8]}"
                    client_id_file.parent.mkdir(parents=True, exist_ok=True)
                    client_id_file.write_text(client_id)
        
        # Register with server
        if not self.register_with_server(client_id):
            logger.error("Failed to register with server. Exiting.")
            return
        
        logger.info(f"Client Worker Service running (ID: {client_id})")
        logger.info(f"Polling server every {self.poll_interval} seconds...")
        
        try:
            while self.running:
                # Send heartbeat
                self.send_heartbeat(client_id)
                
                # Poll server for pending operations
                try:
                    response = self.session.get(
                        f"{self.server_url}/api/client/pending/{client_id}/"
                    )
                    if response.status_code == 200:
                        data = response.json()
                        operations = data.get('operations', [])
                        for op in operations:
                            self._process_operation(op)
                except Exception as e:
                    logger.error(f"Error polling server: {e}")
                
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            logger.info("Shutting down Client Worker Service...")
            self.running = False
        finally:
            # Unregister on shutdown
            try:
                self.unregister_from_server(client_id)
            except Exception as e:
                logger.error(f"Error unregistering on shutdown: {e}")
    
    def _process_operation(self, operation: Dict[str, Any]):
        """Process a pending operation from the server"""
        op_type = operation.get('type')
        operation_id = operation.get('id')
        game_id = operation.get('game_id')
        local_path = operation.get('local_save_path')
        username = operation.get('username')
        game_name = operation.get('game_name')
        save_folder_number = operation.get('save_folder_number')
        
        logger.info(f"Processing operation {operation_id}: {op_type} for game {game_id}")
        logger.info(f"Operation details: username={username}, game_name={game_name}, local_path={local_path}, save_folder={save_folder_number}")
        
        if save_folder_number is None:
            logger.error(f"Operation {operation_id} missing save_folder_number")
            return
        
        if op_type == 'save':
            result = self.save_game(game_id, local_path, username, game_name, save_folder_number)
        elif op_type == 'load':
            result = self.load_game(game_id, local_path, username, game_name, save_folder_number)
        else:
            logger.error(f"Unknown operation type: {op_type}")
            return
        
        # Log the result
        if result.get('success'):
            logger.info(f"Operation {operation_id} succeeded: {result.get('message', 'No message')}")
        else:
            logger.error(f"Operation {operation_id} failed: {result.get('error', result.get('message', 'Unknown error'))}")
        
        # Report result back to server
        try:
            response = self.session.post(
                f"{self.server_url}/api/client/complete/{operation_id}/",
                json=result
            )
            if response.status_code == 200:
                logger.info(f"Operation {operation_id} result reported to server successfully")
            else:
                logger.error(f"Failed to report operation result: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Failed to report operation result: {e}")


def main():
    """Main entry point"""
    import argparse
    
    # Check for server URL in environment variable first
    server_url = os.getenv('SAVENLOAD_SERVER_URL', '').strip()
    
    parser = argparse.ArgumentParser(description='SaveNLoad Client Worker Service')
    parser.add_argument('--server', default=server_url, 
                       help='Django server URL (defaults to SAVENLOAD_SERVER_URL env var)')
    parser.add_argument('--poll-interval', type=int, default=5, help='Poll interval in seconds')
    
    args = parser.parse_args()
    
    if not args.server:
        logger.error("Server URL is required. Set SAVENLOAD_SERVER_URL environment variable or use --server argument.")
        parser.print_help()
        sys.exit(1)
    
    try:
        service = ClientWorkerService(args.server, args.poll_interval)
        service.run()
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

