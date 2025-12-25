"""
Client Worker Service using Rclone
Runs on client PC to handle save/load operations - rclone does all the heavy lifting
"""
import os
import sys
import time
import signal
import requests
import webbrowser
import threading
import shutil
import zipfile
import tempfile
import subprocess
import platform
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List, Callable
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from dotenv import load_dotenv
from rich.console import Console, Group
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rclone_client import RcloneClient, RCLONE_TRANSFERS

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

# Add constants at the top after imports, before the class
RCLONE_TRANSFERS = 10  # This might already exist, but add if not

# Client worker configuration constants
HEARTBEAT_INTERVAL = 5  # Heartbeat interval in seconds
DEFAULT_POLL_INTERVAL = 1  # Default polling interval in seconds

class ClientWorkerServiceRclone:
    """Service that runs on client PC - rclone handles all file operations"""
    
    def __init__(self, server_url: str, poll_interval: int = DEFAULT_POLL_INTERVAL, remote_name: str = 'ftp'):
        """
        Initialize client worker service with rclone
        
        Args:
            server_url: Base URL of the Django server
            poll_interval: How often to poll for pending operations (seconds)
            remote_name: Name of rclone remote (default: 'ftp')
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
        self.linked_user = None  # Track ownership status
        
        # Setup rich console for formatted output
        self.console = Console()
        
        # Setup rclone client - it handles everything
        self.rclone_client = RcloneClient(remote_name=remote_name)
    
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
    
    # ========== HELPER METHODS FOR CODE REUSE ==========
    
    def _create_progress_callback(self, operation_id: Optional[int]) -> Optional[Callable]:
        """
        Create a progress callback function if operation_id is provided
        
        Args:
            operation_id: Optional operation ID for progress tracking
            
        Returns:
            Progress callback function or None
        """
        if operation_id:
            return lambda current, total, msg: self._update_progress(operation_id, current, total, msg)
        return None
    
    def _sanitize_game_name(self, game_name: str) -> str:
        """
        Sanitize game name for use in file paths
        
        Args:
            game_name: Original game name
            
        Returns:
            Sanitized game name safe for file paths
        """
        safe_name = "".join(c for c in game_name if c.isalnum() or c in (' ', '-', '_')).strip()
        return safe_name.replace(' ', '_')
    
    def _build_remote_path_base(self, username: str, game_name: str, 
                                save_folder_number: Optional[int] = None,
                                remote_path: Optional[str] = None,
                                path_index: Optional[int] = None) -> str:
        """
        Build base remote path with optional path_index support
        
        Args:
            username: Username for path
            game_name: Game name (will be sanitized)
            save_folder_number: Optional save folder number
            remote_path: Optional custom remote path (base path like "username/gamename/save_1")
            path_index: Optional path index (1-based) to append path_X subfolder
            
        Returns:
            Remote path string (includes path_X if path_index provided)
        """
        if remote_path:
            base_path = remote_path.replace('\\', '/').strip('/')
        else:
            safe_game_name = self._sanitize_game_name(game_name)
            path_parts = [username, safe_game_name]
            
            if save_folder_number is not None:
                path_parts.append(f"save_{save_folder_number}")
            
            base_path = '/'.join(path_parts)
        
        # Append path_X if path_index is provided (for multi-path support)
        if path_index is not None:
            base_path = f"{base_path}/path_{path_index}"
        
        return base_path
    
    def _create_error_response(self, error_message: str, **kwargs) -> Dict[str, Any]:
        """
        Create standardized error response dictionary
        
        Args:
            error_message: Error message string
            **kwargs: Additional fields to include in response
            
        Returns:
            Error response dictionary
        """
        response = {'success': False, 'error': error_message}
        response.update(kwargs)
        return response
    
    def _create_success_response(self, message: str, **kwargs) -> Dict[str, Any]:
        """
        Create standardized success response dictionary
        
        Args:
            message: Success message string
            **kwargs: Additional fields to include in response
            
        Returns:
            Success response dictionary
        """
        response = {'success': True, 'message': message}
        response.update(kwargs)
        return response
    
    def _handle_operation_exception(self, operation_name: str, exception: Exception) -> Dict[str, Any]:
        """
        Handle exceptions during operations with consistent error reporting
        
        Args:
            operation_name: Name of the operation (e.g., 'Save', 'Load')
            exception: Exception that was raised
            
        Returns:
            Error response dictionary
        """
        error_msg = f'{operation_name} operation failed: {str(exception)}'
        print(f"Error: {error_msg}")
        return self._create_error_response(error_msg)
    
    def _safe_console_print(self, message: str, style: str = ""):
        """
        Safely print to console with error handling
        
        Args:
            message: Message to print
            style: Optional rich style string
        """
        try:
            if style:
                self.console.print(message, style=style)
            else:
                self.console.print(message)
        except Exception:
            pass  # Console might be closed, but continue execution
    
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
                 username: str, game_name: str, save_folder_number: int, 
                 remote_path: Optional[str] = None, operation_id: Optional[int] = None,
                 path_index: Optional[int] = None) -> Dict[str, Any]:
        """Save game - rclone handles everything with parallel transfers"""
        print(f"Backing up save files...")
        
        if not os.path.exists(local_save_path):
            return self._create_error_response(
                'Oops! You don\'t have any save files to save. Maybe you haven\'t played the game yet, or the save location is incorrect.'
            )
        
        try:
            if os.path.isdir(local_save_path):
                # Check if directory is empty
                file_count = 0
                for root, dirs, files in os.walk(local_save_path):
                    file_count += len(files)
                    if file_count > 0:
                        break  # Found at least one file, no need to continue
                
                if file_count == 0:
                    return self._create_error_response(
                        'The save directory is empty. There are no files to save. Make sure you have played the game and saved your progress.'
                    )
                
                # Create progress callback using helper
                progress_callback = self._create_progress_callback(operation_id)
                
                # Build remote path with path_index support
                remote_path_custom = self._build_remote_path_base(
                    username, game_name, save_folder_number, remote_path, path_index
                )
                
                # Use remote_path_custom directly - it now includes path_X if path_index provided
                success, message, uploaded_files, failed_files, bytes_transferred, files_transferred = self.rclone_client.upload_directory(
                    local_dir=local_save_path,
                    username=username,
                    game_name=game_name,
                    folder_number=save_folder_number,
                    remote_path_custom=remote_path_custom,
                    path_index=None,  # Already included in remote_path_custom
                    transfers=RCLONE_TRANSFERS,  # Parallel transfers
                    progress_callback=progress_callback
                )
                
                if success:
                    # Check if anything was actually transferred
                    if bytes_transferred == 0:
                        return self._create_error_response(
                            'No files were transferred. The save directory appears to be empty or contains no valid files to upload.'
                        )
                    
                    print(f"Upload complete")
                    return self._create_success_response(
                        message,
                        uploaded_files=uploaded_files
                    )
                else:
                    print(f"Upload failed: {message}")
                    return self._create_error_response(
                        message,
                        uploaded_files=uploaded_files,
                        failed_files=failed_files
                    )
            else:
                # Single file upload - check if file is empty
                file_size = os.path.getsize(local_save_path)
                if file_size == 0:
                    return self._create_error_response(
                        'The save file is empty (0 bytes). There is nothing to save.'
                    )
                
                print(f"Uploading single file: {os.path.basename(local_save_path)}")
                
                # Create progress callback using helper
                progress_callback = self._create_progress_callback(operation_id)
                
                # Build remote path with path_index support
                remote_path_custom = self._build_remote_path_base(
                    username, game_name, save_folder_number, remote_path, path_index
                )
                
                success, message, bytes_transferred = self.rclone_client.upload_save(
                    username=username,
                    game_name=game_name,
                    local_file_path=local_save_path,
                    folder_number=save_folder_number,
                    remote_filename=os.path.basename(local_save_path),
                    remote_path_custom=remote_path_custom,
                    path_index=None,  # Already included in remote_path_custom
                    progress_callback=progress_callback
                )
                
                if success:
                    # Check if anything was actually transferred
                    if bytes_transferred == 0:
                        return self._create_error_response(
                            'No data was transferred. The save file appears to be empty.'
                        )
                    
                    print(f"Upload complete: {os.path.basename(local_save_path)}")
                    return self._create_success_response(message)
                else:
                    print(f"Upload failed: {message}")
                    return self._create_error_response(message)
                    
        except Exception as e:
            return self._handle_operation_exception('Save', e)
    
    def load_game(self, game_id: int, local_save_path: str,
                 username: str, game_name: str, save_folder_number: int, 
                 remote_path: Optional[str] = None, operation_id: Optional[int] = None,
                 path_index: Optional[int] = None) -> Dict[str, Any]:
        """Load game - rclone handles everything with parallel transfers"""
        print(f"Preparing to download save files...")
        
        try:
            # Build remote path with path_index support
            remote_path_base = self._build_remote_path_base(
                username, game_name, save_folder_number, remote_path, path_index
            )
            
            # Detect if remote path includes path_X folder (e.g., path_1, path_2)
            # If so, we need to strip it to avoid creating path_X subfolder locally
            strip_prefix = None
            if path_index is not None:
                strip_prefix = f"path_{path_index}"
            
            # Ensure local directory exists
            if os.path.isfile(local_save_path):
                local_save_path = os.path.dirname(local_save_path)
            
            try:
                os.makedirs(local_save_path, exist_ok=True)
            except OSError as e:
                print(f"Error: Failed to create directory - {str(e)}")
                return self._create_error_response(
                    f'Failed to create directory: {local_save_path} - {str(e)}'
                )
            
            if not os.path.isdir(local_save_path):
                return self._create_error_response(
                    f'Local save path is not a directory: {local_save_path}'
                )
            
            # Create progress callback using helper
            progress_callback = self._create_progress_callback(operation_id)
            
            # Use remote_path_base which includes path_X if path_index provided
            # Pass strip_prefix to avoid creating path_X subfolder locally
            success, message, downloaded_files, failed_files = self.rclone_client.download_directory(
                remote_path_base=remote_path_base,
                local_dir=local_save_path,
                transfers=RCLONE_TRANSFERS,  # Parallel transfers
                progress_callback=progress_callback,
                strip_path_prefix=strip_prefix  # Strip path_X to avoid creating subfolder
            )
            
            if success:
                print(f"Download complete")
                return self._create_success_response(
                    message,
                    downloaded_files=downloaded_files
                )
            else:
                print(f"Download failed: {message}")
                return self._create_error_response(
                    message,
                    downloaded_files=downloaded_files,
                    failed_files=failed_files
                )
                    
        except Exception as e:
            return self._handle_operation_exception('Load', e)
    
    def list_saves(self, game_id: int, username: str, game_name: str, 
                  save_folder_number: int, remote_path: Optional[str] = None,
                  path_index: Optional[int] = None) -> Dict[str, Any]:
        """List all save files - rclone handles it"""
        print(f"Listing save files...")
        
        try:
            # Update to use _build_remote_path_base with path_index
            remote_path_base = self._build_remote_path_base(
                username, game_name, save_folder_number, remote_path, path_index
            )
            success, files, directories, message = self.rclone_client.list_saves(
                username=username,
                game_name=game_name,
                folder_number=save_folder_number,
                remote_path_custom=remote_path_base
            )
            
            if not success:
                return self._create_error_response(f'Failed to list saves: {message}')
            
            print(f"Found {len(files)} file(s) and {len(directories)} directory(ies)")
            return self._create_success_response(
                message,
                files=files,
                directories=directories
            )
        except Exception as e:
            return self._handle_operation_exception('List', e)
    
    def delete_save_folder(self, game_id: int, username: str, game_name: str,
                          save_folder_number: int, remote_path: Optional[str] = None,
                          operation_id: Optional[int] = None,
                          path_index: Optional[int] = None) -> Dict[str, Any]:
        """Delete save folder - rclone handles it"""
        print(f"Deleting save folder...")
        
        if not remote_path:
            return self._create_error_response(
                'Remote path is required for delete operation'
            )
        
        try:
            # Update to use _build_remote_path_base with path_index
            remote_path_base = self._build_remote_path_base(
                username, game_name, save_folder_number, remote_path, path_index
            )
            # Let rclone delete it
            success, message = self.rclone_client.delete_directory(remote_path_base)
            
            if success:
                print(f"Delete complete")
                return self._create_success_response(message)
            else:
                print(f"Delete failed: {message}")
                return self._create_error_response(message)
                    
        except Exception as e:
            return self._handle_operation_exception('Delete', e)
    
    def backup_all_saves(self, game_id: int, username: str, game_name: str,
                        operation_id: Optional[int] = None) -> Dict[str, Any]:
        """Backup all saves - download using rclone, zip, and save to Downloads folder"""
        print(f"Backing up all saves for {game_name}...")
        
        try:
            # Build base remote path using helper
            remote_path_base = self._build_remote_path_base(username, game_name)
            
            # Create temp directory for downloads
            temp_dir = tempfile.mkdtemp(prefix='sn_backup_')
            print(f"Downloading from FTP to temp directory: {temp_dir}")
            
            try:
                # Create progress callback using helper
                progress_callback = self._create_progress_callback(operation_id)
                
                # Download all saves using rclone
                success, message, downloaded_files, failed_files = self.rclone_client.download_directory(
                    remote_path_base=remote_path_base,
                    local_dir=temp_dir,
                    transfers=RCLONE_TRANSFERS,
                    progress_callback=progress_callback
                )
                
                if not success:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return self._create_error_response(f'Failed to download saves: {message}')
                
                # Check if we got any files
                if not os.listdir(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return self._create_error_response('No save files found to backup')
                
                # Create zip file
                safe_game_name_zip = self._sanitize_game_name(game_name)
                zip_filename = f"{safe_game_name_zip}_saves_bak.zip"
                
                # Get Downloads folder
                downloads_path = Path.home() / 'Downloads'
                if not downloads_path.exists():
                    downloads_path.mkdir(parents=True, exist_ok=True)
                
                zip_path = downloads_path / zip_filename
                
                # Create zip file
                print(f"Creating zip file: {zip_path}")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Get relative path from temp_dir
                            arcname = os.path.relpath(file_path, temp_dir)
                            zipf.write(file_path, arcname)
                
                # Clean up temp directory
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                print(f"Backup complete: {zip_path}")
                return self._create_success_response(
                    f'Backup saved to: {zip_path}',
                    zip_path=str(zip_path),
                    zip_filename=zip_filename
                )
                
            except Exception as e:
                # Clean up temp directory on error
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise e
                    
        except Exception as e:
            return self._handle_operation_exception('Backup', e)
    
    def open_folder(self, local_path: str, operation_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Open save file location folder(s) in file explorer
        Creates folders if they don't exist before opening
        local_path contains JSON with paths and create_folders flag
        """
        import json
        import subprocess
        import platform
        import os
        
        try:
            # Parse JSON data
            try:
                paths_data = json.loads(local_path)
                save_paths = paths_data.get('paths', [])
                create_folders = paths_data.get('create_folders', False)
                save_folder_number = paths_data.get('save_folder_number')
            except (json.JSONDecodeError, TypeError):
                # Fallback: treat as single path string (backward compatibility)
                save_paths = [local_path] if local_path else []
                create_folders = False
                save_folder_number = None
            
            if not save_paths:
                return self._create_error_response('No save paths provided')
            
            opened_count = 0
            failed_paths = []
            
            for path in save_paths:
                try:
                    # Normalize path
                    normalized_path = os.path.normpath(path)
                    
                    # Create folder if it doesn't exist and create_folders is True
                    if create_folders and not os.path.exists(normalized_path):
                        try:
                            os.makedirs(normalized_path, exist_ok=True)
                            print(f"Created folder: {normalized_path}")
                        except OSError as e:
                            print(f"Warning: Failed to create folder {normalized_path}: {str(e)}")
                            # Continue anyway - try to open even if creation failed
                    
                    # Check if path exists (file or directory)
                    if not os.path.exists(normalized_path):
                        failed_paths.append(f"{normalized_path}: Path does not exist")
                        continue
                    
                    # Determine if it's a file or directory
                    if os.path.isfile(normalized_path):
                        # For files, open the parent directory and select the file
                        folder_path = os.path.dirname(normalized_path)
                        file_name = os.path.basename(normalized_path)
                    else:
                        # For directories, open the directory itself
                        folder_path = normalized_path
                        file_name = None
                    
                    # Open folder in file explorer based on OS
                    system = platform.system()
                    
                    if system == 'Windows':
                        if file_name:
                            # Open folder and select file
                            subprocess.Popen(f'explorer /select,"{normalized_path}"', shell=True)
                        else:
                            # Open folder
                            subprocess.Popen(f'explorer "{folder_path}"', shell=True)
                    elif system == 'Darwin':  # macOS
                        if file_name:
                            subprocess.Popen(['open', '-R', normalized_path])
                        else:
                            subprocess.Popen(['open', folder_path])
                    else:  # Linux
                        # Try common file managers
                        try:
                            subprocess.Popen(['xdg-open', folder_path])
                        except FileNotFoundError:
                            # Fallback to nautilus, dolphin, or thunar
                            for manager in ['nautilus', 'dolphin', 'thunar']:
                                try:
                                    subprocess.Popen([manager, folder_path])
                                    break
                                except FileNotFoundError:
                                    continue
                            else:
                                failed_paths.append(f"{normalized_path}: No file manager found")
                                continue
                    
                    opened_count += 1
                    print(f"Opened folder: {folder_path}")
                    
                except Exception as e:
                    failed_paths.append(f"{path}: {str(e)}")
                    print(f"Error opening {path}: {str(e)}")
            
            if opened_count == len(save_paths):
                return self._create_success_response(
                    f'Successfully opened {opened_count} folder{"s" if opened_count > 1 else ""}'
                )
            elif opened_count > 0:
                return self._create_success_response(
                    f'Opened {opened_count}/{len(save_paths)} folder{"s" if opened_count > 1 else ""}. '
                    f'Failed: {", ".join(failed_paths)}'
                )
            else:
                return self._create_error_response(
                    f'Failed to open any folders: {", ".join(failed_paths)}'
                )
                
        except Exception as e:
            return self._handle_operation_exception('Open Folder', e)
    
    def register_with_server(self, client_id: str) -> bool:
        """Register this client with the Django server"""
        try:
            response = self.session.post(
                f"{self.server_url}/api/client/register/",
                json={'client_id': client_id}
            )
            if response.status_code == 200:
                data = response.json()
                # Parse linked_user from response data if available (nested in data usually, or top level?)
                # API returns {data: {client_id, linked_user}}
                response_data = data_obj = data.get('data', {}) if 'data' in data else data
                self.linked_user = response_data.get('linked_user')
                return True
            return False
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
            if response.status_code == 200:
                data = response.json()
                # API returns {data: {linked_user}}
                response_data = data.get('data', {}) if 'data' in data else data
                new_user = response_data.get('linked_user')
                
                # Check for status change
                if new_user != self.linked_user:
                    if new_user:
                        self._safe_console_print(f"\n[green][OK] Device claimed by user: {new_user}[/green]")
                    else:
                        self._safe_console_print(f"\n[yellow][!] Device unclaimed (waiting for owner)[/yellow]")
                    self.linked_user = new_user
                    
                return True
            return False
        except Exception:
            return False
    
    def _heartbeat_loop(self, client_id: str):
        """Background thread that continuously sends heartbeats"""
        heartbeat_interval = HEARTBEAT_INTERVAL
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
    
    def _shutdown(self, client_id: Optional[str] = None):
        """Perform graceful shutdown - cleanup and unregister from server"""
        if not self.running:
            return  # Already shutting down
        
        self._safe_console_print("\n[yellow]Shutting down gracefully...[/yellow]")
        
        self.running = False
        
        # Wait for heartbeat thread to finish
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._safe_console_print("[dim]Waiting for heartbeat thread...[/dim]")
            self._heartbeat_thread.join(timeout=2)
        
        # Unregister from server
        if client_id:
            self._safe_console_print("[dim]Unregistering from server...[/dim]")
            try:
                self.unregister_from_server(client_id)
            except Exception:
                pass
        
        self._safe_console_print("[green]Shutdown complete.[/green]")
        time.sleep(0.5)  # Brief pause to ensure message is visible
    
    def run(self):
        """Run the service (polling mode)"""
        # ASCII art banner using rich
        ascii_art = """  $$$$$$\\  $$\\       $$$$$$\\ $$$$$$$$\\ $$\\   $$\\ $$$$$$$$\\
  $$  __$$\\ $$ |      \\_$$  _|$$  _____|$$$\\  $$ |\\__$$  __|
  $$ /  \\__|$$ |        $$ |  $$ |      $$$$\\ $$ |   $$ |
  $$ |      $$ |        $$ |  $$$$$\\    $$ $$\\$$ |   $$ |
  $$ |      $$ |        $$ |  $$  __|   $$ \\$$$$ |   $$ |
  $$ |  $$\\ $$ |        $$ |  $$ |      $$ |\\$$$ |   $$ |
  \\$$$$$$  |$$$$$$$$\\ $$$$$$\\ $$$$$$$$\\ $$ | \\$$ |   $$ |
   \\______/ \\________|\\______|\\________|\\__|  \\__|   \\__|"""
        
        # Create centered ASCII art banner
        ascii_text = Text(ascii_art, style="bold")
        
        banner_panel = Panel(
            Align.center(ascii_text),
            border_style="bright_white",
            padding=(1, 2),
            width=80
        )
        self.console.print(banner_panel)
        
        if not self.check_permissions():
            self.console.print("[yellow][WARNING][/yellow] Insufficient permissions - you may need elevated privileges\n")
        
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
            self.console.print("[red][ERROR][/red] Failed to register with server. Exiting.")
            return
        
        self._current_client_id = client_id
        
        # Check rclone status
        rclone_success, rclone_message = self.rclone_client.check_status()
        rclone_status = "[green][OK][/green]" if rclone_success else "[red][FAIL][/red]"
        
        # Status output using rich Panel with ASCII-safe indicators
        # Status output using rich Panel with ASCII-safe indicators
        owner_status = f"[green][OK][/green] Owned by: {self.linked_user}" if self.linked_user else "[yellow][!][/yellow] Waiting for Claim"
        
        status_content = f"""[green][OK][/green] Connected to server
[green][OK][/green] Service running (polling every {self.poll_interval}s)
[green][OK][/green] Client ID: {client_id}
{rclone_status} {rclone_message}
{owner_status}"""
        
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, args=(client_id,), daemon=True)
        self._heartbeat_thread.start()
        status_content += f"\n[green][OK][/green] Heartbeat active (every {HEARTBEAT_INTERVAL}s)"
        
        status_panel = Panel(
            status_content,
            title="[bold]STATUS[/bold]",
            border_style="bright_white",
            padding=(1, 2),
            width=80
        )
        self.console.print(status_panel)
        
        # Open browser to server URL for convenience (so user can login and claim)
        try:
            webbrowser.open(self.server_url)
        except Exception:
            pass
        
        # Important message panel
        info_panel = Panel(
            "Do not close this terminal window.\n"
            "The service must remain running to process save/load operations.\n"
            "Press [bold]Ctrl+C[/bold] to stop the service gracefully.",
            title="[bold yellow]IMPORTANT[/bold yellow]",
            border_style="yellow",
            padding=(1, 2),
            width=80
        )
        self.console.print()
        self.console.print(info_panel)
        
        # Server URL at the bottom - make it stand out
        server_url_panel = Panel(
            Align.center(f"[bold bright_cyan]{self.server_url}[/bold bright_cyan]"),
            title="[bold bright_cyan]Server URL[/bold bright_cyan]",
            border_style="bright_cyan",
            padding=(1, 2),
            width=80
        )
        self.console.print()
        self.console.print(server_url_panel)
        self.console.print()
        
        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            """Handle shutdown signals"""
            self._shutdown(client_id)
            sys.exit(0)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
        
        # Windows-specific: Handle console close event
        if platform.system() == 'Windows':
            try:
                import ctypes
                from ctypes import wintypes
                
                # Define handler function type
                HandlerRoutine = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)
                
                # Handler for console close event
                def console_handler(dwCtrlType):
                    if dwCtrlType == 0:  # CTRL_CLOSE_EVENT
                        self._shutdown(client_id)
                        return True  # Handled
                    return False  # Not handled, let default handler process it
                
                # Register console control handler
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleCtrlHandler(HandlerRoutine(console_handler), True)
            except Exception:
                pass  # Fallback to signal handlers if this fails
        
        try:
            while self.running:
                try:
                    response = self.session.get(
                        f"{self.server_url}/api/client/pending/{client_id}/",
                        timeout=5
                    )
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Update linked user status if changed (faster than heartbeat)
                        # This fixes the delay issue where unclaim took 10s+ to reflect
                        new_user = data.get('linked_user')
                        if new_user != self.linked_user:
                            if new_user:
                                self._safe_console_print(f"\n[green][OK] Device claimed by user: {new_user}[/green]")
                            else:
                                self._safe_console_print(f"\n[yellow][!] Device unclaimed (waiting for owner)[/yellow]")
                            self.linked_user = new_user
                            
                        operations = data.get('operations', [])
                        for op in operations:
                            self._process_operation(op)
                except Exception:
                    pass
                
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            # This will be caught by signal handler, but handle it here too
            self._shutdown(client_id)
        finally:
            # Final cleanup (in case signal handler didn't run)
            if self.running:
                self._shutdown(client_id)
    
    def _process_operation(self, operation: Dict[str, Any]):
        """Process a pending operation from the server"""
        op_type = operation.get('type')
        operation_id = operation.get('id')
        game_id = operation.get('game_id')
        local_path = operation.get('local_save_path')
        username = operation.get('username')
        game_name = operation.get('game_name')
        save_folder_number = operation.get('save_folder_number')
        remote_path = operation.get('remote_path')  # Base path like "username/gamename/save_1"
        path_index = operation.get('path_index')  # Extract path_index from operation
        
        op_type_display = op_type.capitalize()
        print(f"\nProcessing: {op_type_display} operation for {game_name}")
        
        # For delete operations, remote_path is sufficient (can delete entire directories)
        if op_type == 'delete' and not remote_path:
            print(f"Error: Delete operation missing remote_path")
            return
        
        if op_type in ['save', 'load', 'list'] and save_folder_number is None:
            print(f"Error: Operation missing required information")
            return
        
        # Backup doesn't require save_folder_number
        if op_type == 'backup' and not username:
            print(f"Error: Backup operation missing username")
            return
        
        # Pass path_index to operations that need it
        if op_type == 'save':
            result = self.save_game(game_id, local_path, username, game_name, save_folder_number, remote_path, operation_id, path_index)
        elif op_type == 'load':
            result = self.load_game(game_id, local_path, username, game_name, save_folder_number, remote_path, operation_id, path_index)
        elif op_type == 'list':
            result = self.list_saves(game_id, username, game_name, save_folder_number, remote_path, path_index)
        elif op_type == 'delete':
            result = self.delete_save_folder(game_id, username, game_name, save_folder_number, remote_path, operation_id, path_index)
        elif op_type == 'backup':
            result = self.backup_all_saves(game_id, username, game_name, operation_id)
        elif op_type == 'open_folder':
            result = self.open_folder(local_path, operation_id)
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
    parser.add_argument('--server', 
                       default=os.getenv('SAVENLOAD_SERVER_URL'),
                       help='Django server URL (defaults to SAVENLOAD_SERVER_URL env var)')
    parser.add_argument('--poll-interval', type=int, default=DEFAULT_POLL_INTERVAL, help='Poll interval in seconds')
    parser.add_argument('--remote', default='ftp', help='Rclone remote name (default: ftp)')
    
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

