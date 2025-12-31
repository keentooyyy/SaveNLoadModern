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
import redis

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


# Client worker configuration constants
HEARTBEAT_INTERVAL = 5  # Heartbeat interval in seconds (how often to update Redis heartbeat)
WORKER_HEARTBEAT_TTL = 10  # Worker heartbeat TTL in seconds (must match server's WORKER_HEARTBEAT_TTL)

_single_instance_handle = None  # Hold mutex/lock handle so it stays alive for process lifetime.

def _show_single_instance_message():
    # Keep the user-facing text in one place for both UI and console output.
    message = "SaveNLoad Client Worker is already running. Close the existing instance before starting a new one."
    try:
        print(message)
        # Pause so the message is readable in an .exe console window.
        if sys.stdin and sys.stdin.isatty():
            input("Press Enter to close...")
    except Exception:
        pass

def _set_console_title(title: str):
    # Windows console title defaults to the exe path; override for readability.
    if platform.system() == 'Windows':
        try:
            os.system(f"title {title}")
        except Exception:
            pass
    else:
        # ANSI escape for most xterm-compatible terminals.
        try:
            sys.stdout.write(f"\x1b]0;{title}\x07")
            sys.stdout.flush()
        except Exception:
            # Fallback via shell in case stdout isn't a TTY or ANSI is blocked.
            try:
                os.system(f'printf "\\033]0;{title}\\007"')
            except Exception:
                pass

def _ensure_single_instance(mutex_name: str, lock_name: str) -> bool:
    global _single_instance_handle
    # Cross-platform lockfile; OS-specific locking API under the hood.
    # mutex_name is kept for compatibility with existing call sites.
    lock_path = Path(tempfile.gettempdir()) / f"{lock_name}.lock"
    try:
        lock_file = open(lock_path, 'a+')
        if platform.system() == 'Windows':
            import msvcrt
            # Lock 1 byte; if already locked, this raises an exception.
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _single_instance_handle = lock_file
        return True
    except Exception:
        _show_single_instance_message()
        return False

class ClientWorkerServiceRclone:
    """Service that runs on client PC - rclone handles all file operations"""
    
    def __init__(self, server_url: str, remote_name: str = 'ftp'):
        """
        Initialize client worker service with rclone
        
        Args:
            server_url: Base URL of the Django server
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
        self.session = requests.Session()
        self.running = False
        self._heartbeat_thread = None
        self._redis_thread = None
        self._current_client_id = None
        self.linked_user = None  # Track ownership status
        
        # Setup rich console for formatted output
        self.console = Console()
        
        # Setup rclone client - it handles everything
        self.rclone_client = RcloneClient(remote_name=remote_name)
        
        # Setup Redis connection (REQUIRED - no fallbacks)
        redis_host = os.getenv('REDIS_HOST')
        redis_port = int(os.getenv('REDIS_PORT'))
        redis_password = os.getenv('REDIS_PASSWORD')
        
        
        # Redis connection is now strictly from env vars

        
        try:
            if redis_password:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    password=redis_password,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
            else:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
            # Test connection - fail if Redis is not available
            self.redis_client.ping()
        except Exception as e:
            error_msg = f"""
[red][ERROR][/red] Redis connection failed - Redis is REQUIRED for this worker.

Attempted to connect to Redis at {redis_host}:{redis_port}
Error: {e}

Please ensure:
1. Redis is running and accessible from your client PC
2. REDIS_HOST environment variable is set correctly (or matches your server URL hostname)
3. Redis port {redis_port} is not blocked by firewall
4. If using Docker, ensure Redis port is exposed: docker-compose.yml should have 'ports: ["6379:6379"]'
"""
            self.console.print(error_msg)
            raise ConnectionError(f"Redis connection failed: {e}. Redis is required - no fallback available.")
    
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
    
    def save_game(self, local_save_path: str, remote_ftp_path: str,
                 operation_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Save game - upload files to pre-built remote FTP path
        
        Args:
            local_save_path: Local path to save files  
            remote_ftp_path: Complete remote FTP path (built by server)
            operation_id: Optional operation ID for progress tracking
        """
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
                
                # Use pre-built remote path from server
                success, message, uploaded_files, failed_files, bytes_transferred, files_transferred = self.rclone_client.upload_directory(
                    local_dir=local_save_path,
                    remote_ftp_path=remote_ftp_path,
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
                
                # Use pre-built remote path from server
                success, message, bytes_transferred = self.rclone_client.upload_save(
                    local_file_path=local_save_path,
                    remote_ftp_path=remote_ftp_path,
                    remote_filename=os.path.basename(local_save_path),
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
    
    def load_game(self, local_save_path: str, remote_ftp_path: str,
                 operation_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Load game - download files from pre-built remote FTP path
        
        Args:
            local_save_path: Local path to restore files to
            remote_ftp_path: Complete remote FTP path (built by server)
            operation_id: Optional operation ID for progress tracking
        """
        print(f"Preparing to download save files...")
        
        try:
            # Detect if remote path includes path_X folder and prepare strip_prefix
            strip_prefix = None
            if '/path_' in remote_ftp_path:
                # Extract path_X from the end
                path_part = remote_ftp_path.split('/')[-1]
                if path_part.startswith('path_'):
                    strip_prefix = path_part
            
            # Ensure local directory exists
            if os.path.isfile(local_save_path):
                local_save_path = os.path.dirname(local_save_path)
            
            # Create directory if it doesn't exist
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
            
            # IMPORTANT: Clear the local directory completely before downloading
            # This ensures a clean restore without old files interfering
            print(f"Clearing local directory: {local_save_path}")
            try:
                import shutil
                for item in os.listdir(local_save_path):
                    item_path = os.path.join(local_save_path, item)
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)
                        print(f"  Deleted file: {item}")
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        print(f"  Deleted folder: {item}")
                print(f"Local directory cleared successfully")
            except Exception as e:
                print(f"Warning: Failed to clear some items from directory: {str(e)}")
                # Continue anyway - partial clear is better than nothing
            
            # Create progress callback using helper
            progress_callback = self._create_progress_callback(operation_id)
            
            # Use pre-built remote path from server
            success, message, downloaded_files, failed_files = self.rclone_client.download_directory(
                remote_ftp_path=remote_ftp_path,
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
    
    def list_saves(self, remote_ftp_path: str) -> Dict[str, Any]:
        """
        List all save files from pre-built remote FTP path
        
        Args:
            remote_ftp_path: Complete remote FTP path (built by server)
        """
        print(f"Listing save files...")
        
        try:
            # Use pre-built remote path from server
            success, files, directories, message = self.rclone_client.list_saves(
                remote_ftp_path=remote_ftp_path
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
    
    def delete_save_folder(self, remote_ftp_path: str, operation_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Delete save folder from pre-built remote FTP path
        
        Args:
            remote_ftp_path: Complete remote FTP path (built by server)
            operation_id: Optional operation ID for progress tracking
        """
        print(f"Deleting save folder...")
        
        try:
            # Use pre-built remote path from server
            success, message = self.rclone_client.delete_directory(remote_ftp_path)
            
            if success:
                print(f"Delete complete")
                return self._create_success_response(message)
            else:
                print(f"Delete failed: {message}")
                return self._create_error_response(message)
                    
        except Exception as e:
            return self._handle_operation_exception('Delete', e)
    
    def backup_all_saves(self, remote_ftp_path: str, operation_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Backup all saves from pre-built remote FTP path
        
        Args:
            remote_ftp_path: Complete remote base path (built by server, e.g., "username/gamename")
            operation_id: Optional operation ID for progress tracking
        """
        # Extract game name from path for zip filename
        path_parts = remote_ftp_path.split('/')
        game_name = path_parts[-1] if len(path_parts) >= 2 else "game"
        
        print(f"Backing up all saves for {game_name}...")
        
        try:
            # Create temp directory for downloads
            temp_dir = tempfile.mkdtemp(prefix='sn_backup_')
            print(f"Downloading from FTP to temp directory: {temp_dir}")
            
            try:
                # Create progress callback using helper
                progress_callback = self._create_progress_callback(operation_id)
                
                # Download all saves using rclone with pre-built path
                success, message, downloaded_files, failed_files = self.rclone_client.download_directory(
                    remote_ftp_path=remote_ftp_path,
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
                
                # Create zip file (use game name from path)
                safe_game_name = game_name.replace(' ', '_')
                zip_filename = f"{safe_game_name}_saves_bak.zip"
                
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
                        # Always open the folder containing the file (no selection)
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
    
    def _check_claim_status(self, client_id: str):
        """Check and update claim status from Redis - can be called from heartbeat or Pub/Sub"""
        try:
            # Check for ownership changes by reading from Redis - NO HTTP CALLS!
            user_id = self.redis_client.hget(f'worker:{client_id}:info', 'user_id')
            username = self.redis_client.hget(f'worker:{client_id}:info', 'username')  # Should be stored by server
            
            # Determine current claim status - user_id is the source of truth
            is_claimed = user_id and user_id != ''
            current_username = username if (username and username != '') else None
            
            # Detect state changes - check if claim status changed
            was_claimed = self.linked_user is not None
            
            if is_claimed:
                # Worker is claimed - use username if available, otherwise show as claimed but unknown user
                if current_username:
                    # Has username - check if it changed
                    if current_username != self.linked_user:
                        self._safe_console_print(f"\n[green][OK] Device claimed by user: {current_username}[/green]")
                        self.linked_user = current_username
                else:
                    # Claimed but no username yet (might be set by another process) - still update state
                    if not was_claimed:
                        self._safe_console_print(f"\n[green][OK] Device claimed (user ID: {user_id})[/green]")
                        self.linked_user = f"user_{user_id}"  # Temporary until username is set
            else:
                # Worker is unclaimed
                if was_claimed:
                    # Was claimed, now unclaimed
                    self._safe_console_print(f"\n[yellow][!] Device unclaimed (waiting for owner)[/yellow]")
                    self.linked_user = None
        except Exception as e:
            # Don't fail on claim status check errors
            pass
    
    def _heartbeat_loop(self, client_id: str):
        """Background thread that continuously updates heartbeat in Redis and checks ownership"""
        heartbeat_interval = HEARTBEAT_INTERVAL
        
        # Validate TTL matches expected range (safety check)
        if WORKER_HEARTBEAT_TTL < 3 or WORKER_HEARTBEAT_TTL > 30:
            print(f"WARNING: WORKER_HEARTBEAT_TTL ({WORKER_HEARTBEAT_TTL}) is outside recommended range (3-30 seconds)")
        
        while self.running:
            try:
                import datetime
                # Refresh heartbeat TTL directly in Redis (must match server's WORKER_HEARTBEAT_TTL)
                # IMPORTANT: This value must match SaveNLoad/services/redis_worker_service.py WORKER_HEARTBEAT_TTL
                self.redis_client.setex(f'worker:{client_id}', WORKER_HEARTBEAT_TTL, '1')
                # Update last_ping in info hash
                self.redis_client.hset(f'worker:{client_id}:info', 'last_ping', datetime.datetime.now().isoformat())
                
                # Check claim status (called from heartbeat loop and Pub/Sub notifications)
                self._check_claim_status(client_id)
                        
            except redis.ConnectionError:
                # Redis connection lost - this is fatal, worker should exit
                self._safe_console_print("[red][ERROR] Redis connection lost - worker cannot continue without Redis[/red]")
                self.running = False
                break
            except Exception as e:
                # Other errors - log but continue
                self._safe_console_print(f"[yellow][WARNING] Heartbeat update failed: {e}[/yellow]")
            
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
        """Run the service (Redis-only mode)"""
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
        redis_channel = f'worker:{client_id}:notify'
        
        status_content = f"""[green][OK][/green] Connected to server
[green][OK][/green] Client ID: {client_id}
{rclone_status} {rclone_message}
[green][OK][/green] Subscribed to Redis channel: {redis_channel}
[green][OK][/green] Heartbeat active (Redis, every {HEARTBEAT_INTERVAL}s)"""
        
        # Add owner status at the bottom
        owner_status = f"[green][OK][/green] Owned by: {self.linked_user}" if self.linked_user else "[yellow][!][/yellow] Waiting for Claim"
        status_content += f"\n{owner_status}"
        
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, args=(client_id,), daemon=True)
        self._heartbeat_thread.start()
        
        # Start Redis Pub/Sub thread
        self._redis_thread = threading.Thread(target=self._redis_subscribe_loop, args=(client_id,), daemon=True)
        self._redis_thread.start()
        
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
        
        # Redis Pub/Sub thread handles all operations - just wait for shutdown
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            # This will be caught by signal handler, but handle it here too
            self._shutdown(client_id)
        finally:
            # Final cleanup (in case signal handler didn't run)
            if self.running:
                self._shutdown(client_id)
    
    def _redis_subscribe_loop(self, client_id: str):
        """Subscribe to Redis Pub/Sub channel for real-time operation notifications"""
        pubsub = self.redis_client.pubsub()
        channel = f'worker:{client_id}:notify'
        
        try:
            pubsub.subscribe(channel)
            
            # Fetch any pending operations immediately
            self._fetch_and_process_operations(client_id)
            
            while self.running:
                try:
                    message = pubsub.get_message(timeout=1.0, ignore_subscribe_messages=True)
                    if message and message['type'] == 'message':
                        message_data = message.get('data', '')
                        if isinstance(message_data, bytes):
                            message_data = message_data.decode('utf-8')
                        
                        # Check if it's a claim status change notification
                        if message_data == 'claim_status_changed':
                            # Immediately check claim status (don't wait for next heartbeat)
                            self._check_claim_status(client_id)
                        else:
                            # New operation notification - fetch operations
                            self._safe_console_print(f"[cyan][*] Received operation notification via Redis Pub/Sub[/cyan]")
                            self._fetch_and_process_operations(client_id)
                except redis.ConnectionError:
                    # Redis connection lost - this is fatal
                    self._safe_console_print("[red][ERROR] Redis connection lost - worker cannot continue without Redis[/red]")
                    self.running = False
                    break
                except Exception as e:
                    # Continue on other errors
                    pass
        except Exception as e:
            self._safe_console_print(f"[red][ERROR] Redis Pub/Sub error: {e} - worker cannot continue[/red]")
            self.running = False
        finally:
            try:
                pubsub.close()
            except:
                pass
    
    def _fetch_and_process_operations(self, client_id: str):
        """Fetch pending operations directly from Redis and process them"""
        try:
            # Read operations directly from Redis - no HTTP polling!
            operation_ids = self.redis_client.lrange(f'worker:{client_id}:operations', 0, -1)
            
            if not operation_ids:
                return
            
            # Linked user status is already tracked in heartbeat loop - no HTTP needed
            
            # Process each pending operation
            operations_to_remove = []
            for operation_id in operation_ids:
                # Get operation hash from Redis
                operation_hash = self.redis_client.hgetall(f'operation:{operation_id}')
                
                if not operation_hash:
                    # Operation doesn't exist, mark for removal
                    operations_to_remove.append(operation_id)
                    continue
                
                status = operation_hash.get('status', '')
                
                # Only process pending operations
                if status == 'pending':
                    # Mark as in_progress in Redis
                    self.redis_client.hset(f'operation:{operation_id}', 'status', 'in_progress')
                    from datetime import datetime
                    self.redis_client.hset(f'operation:{operation_id}', 'started_at', datetime.now().isoformat())
                    
                    # Build operation dict (reading directly from Redis)
                    operation_dict = {
                        'id': operation_id,
                        'type': operation_hash.get('type', ''),
                        'local_save_path': operation_hash.get('local_save_path', ''),
                        'save_folder_number': int(operation_hash['save_folder_number']) if operation_hash.get('save_folder_number') else None,
                        'remote_ftp_path': operation_hash.get('remote_ftp_path', ''),  # NEW: Pre-built FTP path from server
                        'username': operation_hash.get('username', self.linked_user or ''),  # From hash or cached
                        'game_id': int(operation_hash.get('game_id')) if operation_hash.get('game_id') else None,
                    }
                    
                    # Process the operation
                    self._process_operation(operation_dict)
            
            # Remove invalid operation IDs from list
            for operation_id in operations_to_remove:
                self.redis_client.lrem(f'worker:{client_id}:operations', 0, operation_id)
                
        except redis.ConnectionError:
            # Redis connection lost - fatal error
            self._safe_console_print("[red][ERROR] Redis connection lost - worker cannot continue without Redis[/red]")
            self.running = False
        except Exception as e:
            # Silently handle other errors
            pass
    
    def _process_operation(self, operation: Dict[str, Any]):
        """Process a pending operation from the server"""
        op_type = operation.get('type')
        operation_id = operation.get('id')
        local_path = operation.get('local_save_path')
        remote_ftp_path = operation.get('remote_ftp_path')  # Pre-built complete FTP path from server
        
        op_type_display = op_type.capitalize()
        print(f"\nProcessing: {op_type_display} operation")
        
        # Validate required data based on operation type
        if op_type in ['save', 'load'] and not local_path:
            print(f"Error: Operation missing local path")
            return
        
        if op_type in ['save', 'load', 'list', 'delete', 'backup'] and not remote_ftp_path:
            print(f"Error: Operation missing remote FTP path")
            return
        
        # Call simplified methods with pre-built remote_ftp_path
        if op_type == 'save':
            result = self.save_game(local_path, remote_ftp_path, operation_id)
        elif op_type == 'load':
            result = self.load_game(local_path, remote_ftp_path, operation_id)
        elif op_type == 'list':
            result = self.list_saves(remote_ftp_path)
        elif op_type == 'delete':
            result = self.delete_save_folder(remote_ftp_path, operation_id)
        elif op_type == 'backup':
            result = self.backup_all_saves(remote_ftp_path, operation_id)
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
            response = self.session.post(
                f"{self.server_url}/api/client/complete/{operation_id}/",
                json=result
            )
            if response.status_code != 200:
                print(f"Warning: Complete operation returned status {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Error: Failed to mark operation as complete: {e}")


def main():
    """Main entry point"""
    import argparse
    
    server_url = os.getenv('SAVENLOAD_SERVER_URL', '').strip()
    
    parser = argparse.ArgumentParser(description='SaveNLoad Client Worker Service (Rclone)')
    parser.add_argument('--server', 
                       default=os.getenv('SAVENLOAD_SERVER_URL'),
                       help='Django server URL (defaults to SAVENLOAD_SERVER_URL env var)')
    parser.add_argument('--remote', default='ftp', help='Rclone remote name (default: ftp)')
    
    args = parser.parse_args()

    _set_console_title("SaveNLoad Client Worker")

    if not _ensure_single_instance("Global\\SaveNLoadClientWorker", "savenload_client_worker"):
        sys.exit(1)

    if not args.server:
        print("Error: Server URL is required. Set SAVENLOAD_SERVER_URL environment variable or use --server argument.")
        parser.print_help()
        sys.exit(1)
    
    try:
        service = ClientWorkerServiceRclone(args.server, args.remote)
        service.run()
    except Exception as e:
        print(f"Error: Service failed - {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()

