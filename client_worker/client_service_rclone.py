"""
Client Worker Service using Rclone
Runs on client PC to handle save/load operations - rclone does all the heavy lifting
"""
import os
import sys
import time
import json
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
from urllib.parse import urlparse
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rclone_client import RcloneClient, RCLONE_TRANSFERS
import websocket

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
HEARTBEAT_INTERVAL = 5  # Heartbeat interval in seconds (WebSocket keepalive)

_single_instance_handle = None  # Hold mutex/lock handle so it stays alive for process lifetime.

def _show_single_instance_message():
    """
    Print a single-instance warning and pause if a console is attached.

    Args:
        None

    Returns:
        None
    """
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
    """
    Set the terminal window title on the current platform.

    Args:
        title: Window title to set.

    Returns:
        None
    """
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

def _ensure_single_instance(lock_name: str) -> bool:
    """
    Acquire a single-instance lock for this worker.

    Args:
        lock_name: Unique lock name (used for lockfile path).

    Returns:
        True if the lock was acquired, False if another instance is running.
    """
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
        # Keep the handle open for the process lifetime to retain the lock.
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

        Returns:
            None
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
                server_url = f'{scheme}://{host}:8001{path}'
        self.server_url = server_url.rstrip('/')
        self.session = requests.Session()
        self.running = False
        self._heartbeat_thread = None
        self._ws_thread = None
        self._ws = None
        self._ws_token = None
        self._ws_connected = False
        self._ws_send_lock = threading.Lock()
        self._current_client_id = None
        self._ws_last_error = None
        self._rclone_status_line = None
        self.linked_user = None  # Track ownership status
        self._active_operations = set()
        self._active_operations_lock = threading.Lock()
        
        # Setup rich console for formatted output
        self.console = Console()
        
        # Setup rclone client - it handles everything
        self.rclone_client = RcloneClient(remote_name=remote_name)
        
        # WebSocket connection is established after registration.

    def _update_progress(self, operation_id: int, current: int, total: int, message: str = ''):
        """
        Send progress update to server.

        Args:
            operation_id: Server operation ID to correlate progress updates.
            current: Current progress value.
            total: Total progress value.
            message: Optional human-readable progress message.

        Returns:
            None
        """
        self._send_ws_message(
            'progress',
            {
                'operation_id': operation_id,
                'current': current,
                'total': total,
                'message': message,
            },
            correlation_id=str(operation_id)
        )
    
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
        self._safe_console_print(f"Error: {error_msg}")
        return self._create_error_response(error_msg)
    
    def _safe_console_print(self, message: str, style: str = ""):
        """
        Safely print to console with error handling
        
        Args:
            message: Message to print
            style: Optional rich style string

        Returns:
            None
        """
        try:
            if style:
                self.console.print(message, style=style)
            else:
                self.console.print(message)
        except Exception:
            pass  # Console might be closed, but continue execution

    def _build_ws_url(self, client_id: str) -> str:
        """
        Build the worker WS URL using the server base URL and auth token.
        
        Args:
            client_id: Worker identifier
        
        Returns:
            str: WebSocket URL
        """
        parsed = urlparse(self.server_url)
        scheme = 'wss' if parsed.scheme == 'https' else 'ws'
        path_prefix = parsed.path.rstrip('/')
        return f"{scheme}://{parsed.netloc}{path_prefix}/ws/worker/{client_id}/?token={self._ws_token}"

    def _send_ws_message(self, message_type: str, payload: Dict[str, Any], correlation_id: Optional[str] = None):
        """
        Send a JSON message over the worker WS connection (no-op if disconnected).
        
        Args:
            message_type: Event type string
            payload: Message payload dict
            correlation_id: Optional correlation ID string
        
        Returns:
            None
        """
        if not self._ws or not self._ws_connected:
            return

        message = {
            'type': message_type,
            'message_id': str(time.time_ns()),
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'correlation_id': correlation_id,
            'payload': payload,
        }

        try:
            # Serialize and send atomically to avoid interleaving.
            with self._ws_send_lock:
                self._ws.send(json.dumps(message))
        except Exception:
            pass

    def _ws_connect_loop(self, client_id: str):
        """
        WS connect/reconnect loop with short backoff.
        
        Args:
            client_id: Worker identifier
        
        Returns:
            None
        """
        while self.running:
            try:
                ws_url = self._build_ws_url(client_id)
                self._ws = websocket.WebSocketApp(
                    ws_url,
                    on_open=self._on_ws_open,
                    on_message=self._on_ws_message,
                    on_close=self._on_ws_close,
                    on_error=self._on_ws_error
                )
                self._ws.run_forever(ping_interval=10, ping_timeout=5)
            except Exception:
                pass

            self._ws_connected = False
            if self.running:
                # Simple reconnect delay to avoid tight loops.
                time.sleep(2)

    def _on_ws_open(self, ws):
        """
        WS open callback.
        
        Args:
            ws: WebSocketApp instance
        
        Returns:
            None
        """
        self._ws_connected = True
        self._ws_last_error = None
        self._safe_console_print("[green][OK][/green] WebSocket connected")
        self._update_status_panel()
        self._send_ws_message('hello', {'client_id': self._current_client_id})

    def _on_ws_close(self, ws, status_code, msg):
        """
        WS close callback.
        
        Args:
            ws: WebSocketApp instance
            status_code: Close status code
            msg: Close message
        
        Returns:
            None
        """
        self._ws_connected = False
        self._ws_last_error = f"Disconnected code={status_code} msg={msg}"
        self._safe_console_print(f"[red][FAIL][/red] WebSocket not connected ({self._ws_last_error})")
        self._update_status_panel()
        if self.running:
            self._safe_console_print("[red][FAIL][/red] Exiting because WebSocket disconnected.")
            self._shutdown(self._current_client_id)
            sys.exit(1)

    def _on_ws_error(self, ws, error):
        """
        WS error callback.
        
        Args:
            ws: WebSocketApp instance
            error: Error object or message
        
        Returns:
            None
        """
        self._ws_connected = False
        self._ws_last_error = f"Error: {error}"
        self._safe_console_print(f"[red][FAIL][/red] WebSocket not connected ({self._ws_last_error})")
        self._update_status_panel()
        if self.running:
            self._safe_console_print("[red][FAIL][/red] Exiting because WebSocket error occurred.")
            self._shutdown(self._current_client_id)
            sys.exit(1)

    def _on_ws_message(self, ws, message):
        """
        WS message callback: routes server events to handlers.
        
        Args:
            ws: WebSocketApp instance
            message: Raw message string
        
        Returns:
            None
        """
        try:
            data = json.loads(message)
        except Exception:
            self._safe_console_print("[yellow][!] WebSocket received invalid JSON[/yellow]")
            return

        message_type = data.get('type')
        payload = data.get('payload') or {}

        if message_type == 'operation':
            # Server is assigning new work.
            self._handle_operation_message(payload)
        elif message_type == 'claim_status':
            # Server is notifying claim/unclaim status.
            self._handle_claim_status(payload)

    def _handle_operation_message(self, operation: Dict[str, Any]):
        """
        Execute a server-sent operation and report completion.
        
        Args:
            operation: Operation payload dict
        
        Returns:
            None
        """
        operation_id = operation.get('id')
        if not operation_id:
            return

        with self._active_operations_lock:
            if operation_id in self._active_operations:
                return
            # Track active ops to prevent duplicates while running.
            self._active_operations.add(operation_id)

        self._send_ws_message('operation_started', {'operation_id': operation_id}, correlation_id=str(operation_id))

        def run_operation():
            try:
                self._process_operation(operation)
            finally:
                with self._active_operations_lock:
                    self._active_operations.discard(operation_id)

        threading.Thread(target=run_operation, daemon=True).start()

    def _handle_claim_status(self, payload: Dict[str, Any]):
        """
        Update local ownership display based on server claim events.
        
        Args:
            payload: Claim status payload dict
        
        Returns:
            None
        """
        claimed = payload.get('claimed', False)
        linked_user = payload.get('linked_user') or None

        if claimed:
            self.linked_user = linked_user or self.linked_user
            owner = self.linked_user or "Unknown"
            self._safe_console_print(f"[green][OK][/green] Owned by: {owner}")
        else:
            self.linked_user = None
            self._safe_console_print("[yellow][!][/yellow] Waiting for Claim")
        self._update_status_panel()

    def _build_status_panel(self) -> Panel:
        """
        Build the status panel shown in the console UI.

        Args:
            None

        Returns:
            Panel to render in the console UI.
        """
        ws_line = "[green][OK][/green] WebSocket connected" if self._ws_connected else "[red][FAIL][/red] WebSocket not connected"
        if not self._ws_connected and self._ws_last_error:
            ws_line = f"{ws_line} ({self._ws_last_error})"

        heartbeat_line = f"[green][OK][/green] Heartbeat active (WebSocket, every {HEARTBEAT_INTERVAL}s)"

        status_content = f"""[green][OK][/green] Connected to server
[green][OK][/green] Client ID: {self._current_client_id}
{self._rclone_status_line}
{ws_line}
{heartbeat_line}"""

        owner_status = f"[green][OK][/green] Owned by: {self.linked_user}" if self.linked_user else "[yellow][!][/yellow] Waiting for Claim"
        status_content += f"\n{owner_status}"

        return Panel(
            status_content,
            title="[bold]STATUS[/bold]",
            border_style="bright_white",
            padding=(1, 2),
            width=80
        )

    def _update_status_panel(self):
        """
        No-op placeholder for future status updates.

        Args:
            None

        Returns:
            None
        """
        return
    
    def check_permissions(self) -> bool:
        """
        Check if we have necessary permissions to access user files.

        Args:
            None

        Returns:
            True if basic access checks pass, False otherwise.
        """
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

        Returns:
            Response dict with success flag and message or error.
        """
        self._safe_console_print("Backing up save files...")
        
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
                    # If rclone reports no transfers, force a resync by purging remote and re-uploading.
                    if bytes_transferred == 0 and files_transferred == 0:
                        self._safe_console_print("No changes detected. Forcing resync...")
                        purge_success, purge_message = self.rclone_client.delete_directory(remote_ftp_path)
                        if not purge_success:
                            return self._create_error_response(
                                f'Failed to clear remote save folder before resync: {purge_message}'
                            )

                        success, message, uploaded_files, failed_files, bytes_transferred, files_transferred = self.rclone_client.upload_directory(
                            local_dir=local_save_path,
                            remote_ftp_path=remote_ftp_path,
                            transfers=RCLONE_TRANSFERS,
                            progress_callback=progress_callback
                        )

                        if not success:
                            self._safe_console_print(f"Upload failed after resync: {message}")
                            return self._create_error_response(
                                message,
                                uploaded_files=uploaded_files,
                                failed_files=failed_files
                            )

                    message = message or 'Upload complete'
                    self._safe_console_print(message)
                    return self._create_success_response(
                        message,
                        uploaded_files=uploaded_files,
                        bytes_transferred=bytes_transferred,
                        files_transferred=files_transferred
                    )
                else:
                    self._safe_console_print(f"Upload failed: {message}")
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
                
                self._safe_console_print(f"Uploading single file: {os.path.basename(local_save_path)}")
                
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
                    
                    self._safe_console_print(f"Upload complete: {os.path.basename(local_save_path)}")
                    return self._create_success_response(message)
                else:
                    self._safe_console_print(f"Upload failed: {message}")
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

        Returns:
            Response dict with success flag and message or error.
        """
        self._safe_console_print("Preparing to download save files...")
        
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
                self._safe_console_print(f"Error: Failed to create directory - {str(e)}")
                return self._create_error_response(
                    f'Failed to create directory: {local_save_path} - {str(e)}'
                )
            
            if not os.path.isdir(local_save_path):
                return self._create_error_response(
                    f'Local save path is not a directory: {local_save_path}'
                )
            
            # IMPORTANT: Clear the local directory completely before downloading
            # This ensures a clean restore without old files interfering
            self._safe_console_print(f"Clearing local directory: {local_save_path}")
            try:
                import shutil
                deleted_files = 0
                deleted_dirs = 0
                for item in os.listdir(local_save_path):
                    item_path = os.path.join(local_save_path, item)
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)
                        deleted_files += 1
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        deleted_dirs += 1
                self._safe_console_print(f"Local directory cleared (files={deleted_files}, folders={deleted_dirs})")
            except Exception as e:
                self._safe_console_print(f"Warning: Failed to clear some items from directory: {str(e)}")
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
                self._safe_console_print("Download complete")
                return self._create_success_response(
                    message,
                    downloaded_files=downloaded_files
                )
            else:
                self._safe_console_print(f"Download failed: {message}")
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

        Returns:
            Response dict with files, directories, and status.
        """
        self._safe_console_print("Listing save files...")
        
        try:
            # Use pre-built remote path from server
            success, files, directories, message = self.rclone_client.list_saves(
                remote_ftp_path=remote_ftp_path
            )
            
            if not success:
                return self._create_error_response(f'Failed to list saves: {message}')
            
            self._safe_console_print(f"Found {len(files)} file(s) and {len(directories)} directory(ies)")
            return self._create_success_response(
                message,
                files=files,
                directories=directories
            )
        except Exception as e:
            return self._handle_operation_exception('List', e)
    
    def delete_save_folder(self, remote_ftp_path: str) -> Dict[str, Any]:
        """
        Delete save folder from pre-built remote FTP path
        
        Args:
            remote_ftp_path: Complete remote FTP path (built by server)

        Returns:
            Response dict with success flag and message or error.
        """
        self._safe_console_print("Deleting save folder...")
        
        try:
            # Use pre-built remote path from server
            success, message = self.rclone_client.delete_directory(remote_ftp_path)
            
            if success:
                self._safe_console_print("Delete complete")
                return self._create_success_response(message)
            else:
                self._safe_console_print(f"Delete failed: {message}")
                return self._create_error_response(message)
                    
        except Exception as e:
            return self._handle_operation_exception('Delete', e)
    
    def backup_all_saves(self, remote_ftp_path: str, operation_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Backup all saves from pre-built remote FTP path
        
        Args:
            remote_ftp_path: Complete remote base path (built by server, e.g., "username/gamename")
            operation_id: Optional operation ID for progress tracking

        Returns:
            Response dict with zip path on success.
        """
        # Extract game name from path for zip filename
        path_parts = remote_ftp_path.split('/')
        game_name = path_parts[-1] if len(path_parts) >= 2 else "game"
        
        self._safe_console_print(f"Backing up all saves for {game_name}...")
        
        try:
            # Create temp directory for downloads
            temp_dir = tempfile.mkdtemp(prefix='sn_backup_')
            self._safe_console_print(f"Downloading from FTP to temp directory: {temp_dir}")
            
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
                self._safe_console_print(f"Creating zip file: {zip_path}")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Get relative path from temp_dir
                            arcname = os.path.relpath(file_path, temp_dir)
                            zipf.write(file_path, arcname)
                
                # Clean up temp directory
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                self._safe_console_print(f"Backup complete: {zip_path}")
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
    
    def open_folder(self, local_path: str) -> Dict[str, Any]:
        """
        Open one or more save paths in the OS file explorer.
        
        Args:
            local_path: Single path string or JSON object string:
                {"paths": ["/path/one", "/path/two"], "create_folders": true}

        Returns:
            Response dict with success flag and message or error.

        If create_folders is true, missing directories are created before opening.
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
                            self._safe_console_print(f"Created folder: {normalized_path}")
                        except OSError as e:
                            self._safe_console_print(f"Warning: Failed to create folder {normalized_path}: {str(e)}")
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
                    self._safe_console_print(f"Opened folder: {folder_path}")
                    
                except Exception as e:
                    failed_paths.append(f"{path}: {str(e)}")
                    self._safe_console_print(f"Error opening {path}: {str(e)}")
            
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
        """
        Register this client with the Django server.
        
        Args:
            client_id: Worker identifier
        
        Returns:
            bool: True on success, False otherwise
        """
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
                # WebSocket auth depends on this token.
                self._ws_token = response_data.get('ws_token')
                return bool(self._ws_token)
            return False
        except Exception:
            return False

    def _heartbeat_loop(self, client_id: str):
        """
        Background thread that continuously sends heartbeats to the server.
        
        Args:
            client_id: Worker identifier
        
        Returns:
            None
        """
        heartbeat_interval = HEARTBEAT_INTERVAL

        while self.running:
            if self._ws_connected:
                # Keep Redis TTL alive via server-side heartbeat handling.
                self._send_ws_message('heartbeat', {'client_id': client_id})

            for _ in range(heartbeat_interval * 10):
                if not self.running:
                    break
                time.sleep(0.1)
    
    def unregister_from_server(self, client_id: str) -> bool:
        """
        Unregister this client from the Django server.

        Args:
            client_id: Worker identifier.

        Returns:
            True on success, False otherwise.
        """
        try:
            response = self.session.post(
                f"{self.server_url}/api/client/unregister/",
                json={'client_id': client_id}
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def _shutdown(self, client_id: Optional[str] = None):
        """
        Perform graceful shutdown - cleanup and unregister from server.

        Args:
            client_id: Optional worker identifier to unregister.

        Returns:
            None
        """
        if not self.running:
            return  # Already shutting down
        
        self._safe_console_print("\n[yellow]Shutting down gracefully...[/yellow]")
        
        self.running = False

        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass

        # No live console to stop.
        
        # Unregister from server
        if client_id:
            self._safe_console_print("[dim]Unregistering from server...[/dim]")
            try:
                self.unregister_from_server(client_id)
            except Exception:
                pass
        
        self._safe_console_print("[green]Shutdown complete.[/green]")
    
    def run(self):
        """
        Run the service (WebSocket mode).

        Args:
            None

        Returns:
            None
        """
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
        self._rclone_status_line = f"{rclone_status} {rclone_message}"
        
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
        
        # Server URL at the bottom - make it stand out
        server_url_panel = Panel(
            Align.center(f"[bold bright_cyan]{self.server_url}[/bold bright_cyan]"),
            title="[bold bright_cyan]Server URL[/bold bright_cyan]",
            border_style="bright_cyan",
            padding=(1, 2),
            width=80
        )
        self.console.print(banner_panel)
        self.console.print(self._build_status_panel())
        self.console.print()
        self.console.print(info_panel)
        self.console.print()
        self.console.print(server_url_panel)

        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, args=(client_id,), daemon=True)
        self._heartbeat_thread.start()

        # Start WebSocket connection loop after registration and status checks.
        self._ws_thread = threading.Thread(target=self._ws_connect_loop, args=(client_id,), daemon=True)
        self._ws_thread.start()

        # Open browser to server URL for convenience (so user can login and claim)
        try:
            webbrowser.open(self.server_url)
        except Exception:
            pass
        
        # WebSocket thread handles all operations - just wait for shutdown
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self._shutdown(client_id)
        finally:
            # Final cleanup (in case signal handler didn't run)
            if self.running:
                self._shutdown(client_id)
    
    def _process_operation(self, operation: Dict[str, Any]):
        """
        Process a pending operation from the server.

        Args:
            operation: Operation payload dict.

        Returns:
            None
        """
        op_type = operation.get('type')
        operation_id = operation.get('id')
        local_path = operation.get('local_save_path')
        remote_ftp_path = operation.get('remote_ftp_path')  # Pre-built complete FTP path from server
        
        op_type_display = op_type.capitalize()
        self._safe_console_print(f"\nProcessing: {op_type_display} operation")

        # Validate required data based on operation type
        if op_type in ['save', 'load'] and not local_path:
            self._safe_console_print("Error: Operation missing local path")
            return

        if op_type in ['save', 'load', 'list', 'delete', 'backup'] and not remote_ftp_path:
            self._safe_console_print("Error: Operation missing remote FTP path")
            return

        # Call simplified methods with pre-built remote_ftp_path
        if op_type == 'save':
            result = self.save_game(local_path, remote_ftp_path, operation_id)
        elif op_type == 'load':
            result = self.load_game(local_path, remote_ftp_path, operation_id)
        elif op_type == 'list':
            result = self.list_saves(remote_ftp_path)
        elif op_type == 'delete':
            result = self.delete_save_folder(remote_ftp_path)
        elif op_type == 'backup':
            result = self.backup_all_saves(remote_ftp_path, operation_id)
        elif op_type == 'open_folder':
            result = self.open_folder(local_path)
        else:
            self._safe_console_print("Error: Unknown operation type")
            return

        if result.get('success'):
            message = result.get('message', 'Operation completed successfully')
            self._safe_console_print(f"Success: {message}")
        else:
            error = result.get('error', result.get('message', 'Unknown error'))
            self._safe_console_print(f"Error: {error}")
        
        result_payload = dict(result)
        result_payload['operation_id'] = operation_id
        self._send_ws_message('complete', result_payload, correlation_id=str(operation_id))


def main():
    """
    Main entry point.

    Args:
        None

    Returns:
        None
    """
    import argparse
    
    server_url = os.getenv('SAVENLOAD_SERVER_URL', '').strip()
    
    parser = argparse.ArgumentParser(description='SaveNLoad Client Worker Service (Rclone)')
    parser.add_argument('--server', 
                       default=os.getenv('SAVENLOAD_SERVER_URL'),
                       help='Django server URL (defaults to SAVENLOAD_SERVER_URL env var)')
    parser.add_argument('--remote', default='ftp', help='Rclone remote name (default: ftp)')
    
    args = parser.parse_args()

    _set_console_title("SaveNLoad Client Worker")

    if not _ensure_single_instance("savenload_client_worker"):
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

