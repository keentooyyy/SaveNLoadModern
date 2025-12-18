"""
Client Worker Service using Rclone
Runs on client PC to handle save/load operations - rclone does all the heavy lifting
"""
import os
import sys
import time
import requests
import webbrowser
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from dotenv import load_dotenv
from rclone_client import RcloneClient

# Load environment variables
if getattr(sys, 'frozen', False):
    exe_dir = Path(sys.executable).parent
    env_path = exe_dir / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()
else:
    load_dotenv()


class ClientWorkerServiceRclone:
    """Service that runs on client PC - rclone handles all file operations"""
    
    def __init__(self, server_url: str, poll_interval: int = 5, remote_name: str = 'smb'):
        """
        Initialize client worker service with rclone
        
        Args:
            server_url: Base URL of the Django server
            poll_interval: How often to poll for pending operations (seconds)
            remote_name: Name of rclone remote (default: 'smb')
        """
        # Add http:// scheme if missing
        if not server_url.startswith(('http://', 'https://')):
            server_url = f'http://{server_url}'
        # Add default port if no port specified
        if '://' in server_url:
            scheme, rest = server_url.split('://', 1)
            if ':' not in rest.split('/')[0]:
                host = rest.split('/')[0]
                path = rest[len(host):] if len(rest) > len(host) else ''
                server_url = f'{scheme}://{host}:8000{path}'
        self.server_url = server_url.rstrip('/')
        self.poll_interval = poll_interval
        self.session = requests.Session()
        self.running = False
        self._heartbeat_thread = None
        self._current_client_id = None
        
        # Get share name from environment
        smb_share = os.getenv('SMB_SHARE', 'n_Saves').strip()
        
        # Setup rclone client - it handles everything
        self.rclone_client = RcloneClient(remote_name=remote_name, share_name=smb_share)
        
        print("Client Worker Service (Rclone) ready")
    
    def _update_progress(self, operation_id: int, current: int, total: int, message: str = ''):
        """Send progress update to server"""
        try:
            self.session.post(
                f"{self.server_url}/api/client/progress/{operation_id}/",
                json={'current': current, 'total': total, 'message': message},
                timeout=2
            )
        except Exception:
            pass
    
    def check_permissions(self) -> bool:
        """Check if we have necessary permissions to access files"""
        try:
            test_path = Path.home() / 'Documents'
            if test_path.exists():
                test_path.stat()
            return True
        except PermissionError:
            print("Warning: Insufficient file permissions")
            return False
    
    def save_game(self, game_id: int, local_save_path: str, 
                 username: str, game_name: str, save_folder_number: int, smb_path: Optional[str] = None,
                 operation_id: Optional[int] = None) -> Dict[str, Any]:
        """Save game - rclone handles everything with parallel transfers"""
        print(f"Backing up save files...")
        
        if not os.path.exists(local_save_path):
            return {
                'success': False,
                'error': 'Oops! You don\'t have any save files to save. Maybe you haven\'t played the game yet, or the save location is incorrect.'
            }
        
        try:
            if os.path.isdir(local_save_path):
                print("Starting upload (rclone handling all transfers with parallel workers)...")
                
                # Just call rclone - it handles everything
                success, message, uploaded_files, failed_files = self.rclone_client.upload_directory(
                    local_dir=local_save_path,
                    username=username,
                    game_name=game_name,
                    folder_number=save_folder_number,
                    smb_path=smb_path,
                    transfers=10  # Parallel transfers
                )
                
                if success:
                    print(f"Upload complete")
                    return {
                        'success': True,
                        'message': message,
                        'uploaded_files': uploaded_files
                    }
                else:
                    print(f"Upload failed: {message}")
                    return {
                        'success': False,
                        'error': message,
                        'uploaded_files': uploaded_files,
                        'failed_files': failed_files
                    }
            else:
                # Single file upload
                print(f"Uploading single file: {os.path.basename(local_save_path)}")
                success, message = self.rclone_client.upload_save(
                    username=username,
                    game_name=game_name,
                    local_file_path=local_save_path,
                    folder_number=save_folder_number,
                    remote_filename=os.path.basename(local_save_path),
                    smb_path=smb_path
                )
                
                if success:
                    print(f"Upload complete: {os.path.basename(local_save_path)}")
                    return {'success': True, 'message': message}
                else:
                    print(f"Upload failed: {message}")
                    return {'success': False, 'error': message}
                    
        except Exception as e:
            print(f"Error: Save operation failed - {str(e)}")
            return {'success': False, 'error': f'Save operation failed: {str(e)}'}
    
    def load_game(self, game_id: int, local_save_path: str,
                 username: str, game_name: str, save_folder_number: int, smb_path: Optional[str] = None,
                 operation_id: Optional[int] = None) -> Dict[str, Any]:
        """Load game - rclone handles everything with parallel transfers"""
        print(f"Preparing to download save files...")
        
        try:
            # Build remote path
            if smb_path:
                remote_path_base = smb_path.replace('\\', '/').strip('/')
            else:
                # Build standard path
                safe_game_name = "".join(c for c in game_name if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_game_name = safe_game_name.replace(' ', '_')
                remote_path_base = f"{username}/{safe_game_name}/save_{save_folder_number}"
            
            # Ensure local directory exists
            if os.path.isfile(local_save_path):
                local_save_path = os.path.dirname(local_save_path)
            
            try:
                os.makedirs(local_save_path, exist_ok=True)
            except OSError as e:
                print(f"Error: Failed to create directory - {str(e)}")
                return {
                    'success': False,
                    'error': f'Failed to create directory: {local_save_path} - {str(e)}'
                }
            
            if not os.path.isdir(local_save_path):
                return {
                    'success': False,
                    'error': f'Local save path is not a directory: {local_save_path}'
                }
            
            print("Starting download (rclone handling all transfers with parallel workers)...")
            
            # Just call rclone - it handles everything
            success, message, downloaded_files, failed_files = self.rclone_client.download_directory(
                remote_path_base=remote_path_base,
                local_dir=local_save_path,
                transfers=10  # Parallel transfers
            )
            
            if success:
                print(f"Download complete")
                return {
                    'success': True,
                    'message': message,
                    'downloaded_files': downloaded_files
                }
            else:
                print(f"Download failed: {message}")
                return {
                    'success': False,
                    'error': message,
                    'downloaded_files': downloaded_files,
                    'failed_files': failed_files
                }
                    
        except Exception as e:
            print(f"Error: Load operation failed - {str(e)}")
            return {'success': False, 'error': f'Load operation failed: {str(e)}'}
    
    def list_saves(self, game_id: int, username: str, game_name: str, 
                  save_folder_number: int, smb_path: Optional[str] = None) -> Dict[str, Any]:
        """List all save files - rclone handles it"""
        print(f"Listing save files...")
        
        try:
            success, files, directories, message = self.rclone_client.list_saves(
                username=username,
                game_name=game_name,
                folder_number=save_folder_number,
                smb_path=smb_path
            )
            
            if not success:
                return {
                    'success': False,
                    'error': f'Failed to list saves: {message}'
                }
            
            print(f"Found {len(files)} file(s) and {len(directories)} directory(ies)")
            return {
                'success': True,
                'files': files,
                'directories': directories,
                'message': message
            }
        except Exception as e:
            print(f"ERROR: List operation failed: {e}")
            return {'success': False, 'error': f'List operation failed: {str(e)}'}
    
    def delete_save_folder(self, game_id: int, username: str, game_name: str,
                          save_folder_number: int, smb_path: Optional[str] = None,
                          operation_id: Optional[int] = None) -> Dict[str, Any]:
        """Delete save folder - rclone handles it"""
        print(f"Deleting save folder...")
        
        if not smb_path:
            return {
                'success': False,
                'error': 'SMB path is required for delete operation'
            }
        
        try:
            # Let rclone delete it
            success, message = self.rclone_client.delete_directory(smb_path)
            
            if success:
                print(f"Delete complete")
                return {
                    'success': True,
                    'message': message
                }
            else:
                print(f"Delete failed: {message}")
                return {
                    'success': False,
                    'error': message
                }
                    
        except Exception as e:
            print(f"Error: Delete operation failed - {str(e)}")
            return {'success': False, 'error': f'Delete operation failed: {str(e)}'}
    
    def register_with_server(self, client_id: str) -> bool:
        """Register this client with the Django server"""
        try:
            response = self.session.post(
                f"{self.server_url}/api/client/register/",
                json={'client_id': client_id}
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def send_heartbeat(self, client_id: str) -> bool:
        """Send heartbeat to Django server"""
        try:
            response = self.session.post(
                f"{self.server_url}/api/client/heartbeat/",
                json={'client_id': client_id},
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def _heartbeat_loop(self, client_id: str):
        """Background thread that continuously sends heartbeats"""
        heartbeat_interval = 10
        while self.running:
            try:
                self.send_heartbeat(client_id)
            except Exception:
                pass
            for _ in range(heartbeat_interval * 10):
                if not self.running:
                    break
                time.sleep(0.1)
    
    def unregister_from_server(self, client_id: str) -> bool:
        """Unregister this client from the Django server"""
        try:
            response = self.session.post(
                f"{self.server_url}/api/client/unregister/",
                json={'client_id': client_id}
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def run(self):
        """Run the service (polling mode)"""
        print("Starting Client Worker Service (Rclone)...")
        
        if not self.check_permissions():
            print("Warning: Insufficient permissions - you may need elevated privileges")
        
        self.running = True
        
        import platform
        import uuid
        
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                           for elements in range(0,2*6,2)][::-1])
            hostname = platform.node() or platform.uname().node
            client_id = f"{hostname}_{mac}"
        except:
            hostname = platform.node() or platform.uname().node or 'unknown'
            try:
                if sys.platform == 'linux':
                    import subprocess
                    machine_id = subprocess.check_output(['cat', '/etc/machine-id']).decode().strip()[:8]
                    client_id = f"{hostname}_{machine_id}"
                else:
                    machine_info = platform.machine() + platform.processor()
                    client_id = f"{hostname}_{hash(machine_info) & 0xffffffff:08x}"
            except:
                client_id_file = Path.home() / '.savenload' / 'client_id.txt'
                if client_id_file.exists():
                    client_id = client_id_file.read_text().strip()
                else:
                    client_id = f"{hostname}_{uuid.uuid4().hex[:8]}"
                    client_id_file.parent.mkdir(parents=True, exist_ok=True)
                    client_id_file.write_text(client_id)
        
        if not self.register_with_server(client_id):
            print("Error: Failed to register with server. Exiting.")
            return
        
        self._current_client_id = client_id
        
        print(f"Connected to server")
        print(f"Service running (checking for operations every {self.poll_interval} second(s))...")
        
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, args=(client_id,), daemon=True)
        self._heartbeat_thread.start()
        print("Heartbeat thread started (sending heartbeats every 10 seconds)")
        
        try:
            webbrowser.open(self.server_url)
        except Exception:
            pass
        
        print(f"\nServer URL: {self.server_url}")
        
        try:
            while self.running:
                try:
                    response = self.session.get(
                        f"{self.server_url}/api/client/pending/{client_id}/",
                        timeout=5
                    )
                    if response.status_code == 200:
                        data = response.json()
                        operations = data.get('operations', [])
                        for op in operations:
                            self._process_operation(op)
                except Exception:
                    pass
                
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.running = False
        finally:
            if self._heartbeat_thread and self._heartbeat_thread.is_alive():
                self._heartbeat_thread.join(timeout=2)
            try:
                self.unregister_from_server(client_id)
            except Exception:
                pass
    
    def _process_operation(self, operation: Dict[str, Any]):
        """Process a pending operation from the server"""
        op_type = operation.get('type')
        operation_id = operation.get('id')
        game_id = operation.get('game_id')
        local_path = operation.get('local_save_path')
        username = operation.get('username')
        game_name = operation.get('game_name')
        save_folder_number = operation.get('save_folder_number')
        smb_path = operation.get('smb_path')
        
        op_type_display = op_type.capitalize()
        print(f"\nProcessing: {op_type_display} operation for {game_name}")
        
        if op_type in ['save', 'load', 'list', 'delete'] and save_folder_number is None:
            print(f"Error: Operation missing required information")
            return
        
        if op_type == 'save':
            result = self.save_game(game_id, local_path, username, game_name, save_folder_number, smb_path, operation_id)
        elif op_type == 'load':
            result = self.load_game(game_id, local_path, username, game_name, save_folder_number, smb_path, operation_id)
        elif op_type == 'list':
            result = self.list_saves(game_id, username, game_name, save_folder_number, smb_path)
        elif op_type == 'delete':
            result = self.delete_save_folder(game_id, username, game_name, save_folder_number, smb_path, operation_id)
        else:
            print(f"Error: Unknown operation type")
            return
        
        if result.get('success'):
            message = result.get('message', 'Operation completed successfully')
            print(f"Success: {message}")
        else:
            error = result.get('error', result.get('message', 'Unknown error'))
            print(f"Error: {error}")
        
        try:
            self.session.post(
                f"{self.server_url}/api/client/complete/{operation_id}/",
                json=result
            )
        except Exception:
            pass


def main():
    """Main entry point"""
    import argparse
    
    server_url = os.getenv('SAVENLOAD_SERVER_URL', '').strip()
    
    parser = argparse.ArgumentParser(description='SaveNLoad Client Worker Service (Rclone)')
    parser.add_argument('--server', default=server_url, 
                       help='Django server URL (defaults to SAVENLOAD_SERVER_URL env var)')
    parser.add_argument('--poll-interval', type=int, default=5, help='Poll interval in seconds')
    parser.add_argument('--remote', default='smb', help='Rclone remote name (default: smb)')
    
    args = parser.parse_args()
    
    if not args.server:
        print("Error: Server URL is required. Set SAVENLOAD_SERVER_URL environment variable or use --server argument.")
        parser.print_help()
        sys.exit(1)
    
    try:
        service = ClientWorkerServiceRclone(args.server, args.poll_interval, args.remote)
        service.run()
    except Exception as e:
        print(f"Error: Service failed - {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()

