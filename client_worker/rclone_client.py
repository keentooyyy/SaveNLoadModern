"""
Rclone-based File Transfer Client for SaveNLoad
Uses rclone CLI for fast, reliable file transfers supporting multiple protocols
"""
import os
import subprocess
import json
import threading
import tempfile
import time
import re
from pathlib import Path
from typing import Optional, List, Tuple, Callable


class RcloneClient:
    """Rclone-based client for fast file transfers
    
    Supports: FTP, SFTP, and many other protocols via rclone
    """
    
    def __init__(self, remote_name: str = 'ftp', rclone_path: Optional[str] = None, 
                 config_path: Optional[str] = None):
        """Initialize rclone client
        
        Args:
            remote_name: Name of the rclone remote (from rclone.conf)
            rclone_path: Path to rclone executable (default: ./rclone/rclone.exe)
            config_path: Path to rclone config file (default: ./rclone/rclone.conf)
        """
        # Determine rclone executable path
        if rclone_path:
            self.rclone_exe = Path(rclone_path)
        else:
            # Default to rclone directory in same folder as this script
            script_dir = Path(__file__).parent
            self.rclone_exe = script_dir / 'rclone' / 'rclone.exe'
        
        # Determine config path
        if config_path:
            self.config_path = Path(config_path)
        else:
            script_dir = Path(__file__).parent
            self.config_path = script_dir / 'rclone' / 'rclone.conf'
        
        # Verify rclone exists
        if not self.rclone_exe.exists():
            raise FileNotFoundError(f"rclone executable not found at: {self.rclone_exe}")
        
        # Verify config exists
        if not self.config_path.exists():
            raise FileNotFoundError(f"rclone config not found at: {self.config_path}")
        
        self.remote_name = remote_name
    
    def _run_rclone(self, command: List[str], timeout: Optional[int] = None, silent: bool = False,
                   progress_callback: Optional[Callable[[int, int, str], None]] = None) -> Tuple[bool, str, str]:
        """Run rclone command and return success, stdout, stderr
        
        Args:
            command: rclone command arguments
            timeout: Optional timeout in seconds
            silent: If True, don't print output (still captures it)
            progress_callback: Optional callback(current, total, message) for progress updates
        """
        log_file = None
        try:
            # Create temporary log file for rclone output
            log_fd, log_file = tempfile.mkstemp(suffix='.log', prefix='rclone_', text=True)
            os.close(log_fd)  # Close the file descriptor, we'll open it separately for reading
            
            # Build full command with config and log file
            full_cmd = [
                str(self.rclone_exe),
                '--config', str(self.config_path),
                '--log-file', log_file,
            ] + command
            
            # Run rclone - show stdout in real-time, use log file for completion check
            process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            stdout_lines = []
            last_progress = {'current': 0, 'total': 0, 'message': ''}
            
            def parse_progress(line: str) -> Optional[Tuple[int, int, str]]:
                """Parse rclone progress from output line
                
                Returns: (current, total, message) or None if no progress found
                """
                # Pattern 1: "Transferred: 105 / 109, 96%" (file count)
                file_count_match = re.search(r'Transferred:\s+(\d+)\s+/\s+(\d+),?\s*(\d+)%?', line)
                if file_count_match:
                    current = int(file_count_match.group(1))
                    total = int(file_count_match.group(2))
                    percentage = int(file_count_match.group(3)) if file_count_match.group(3) else 0
                    message = f"{percentage}% - {current}/{total} files"
                    return (current, total, message)
                
                # Pattern 2: "Transferred: 17.725 MiB / 17.725 MiB, 100%, 2.532 MiB/s, ETA 0s" (bytes)
                byte_match = re.search(r'Transferred:\s+[\d.]+\s+\w+\s+/\s+[\d.]+\s+\w+,\s+(\d+)%', line)
                if byte_match:
                    percentage = int(byte_match.group(1))
                    # Extract speed if available
                    speed_match = re.search(r'([\d.]+\s+\w+/s)', line)
                    speed = speed_match.group(1) if speed_match else ''
                    message = f"{percentage}%{f' @ {speed}' if speed else ''}"
                    # Use percentage to estimate current/total if we don't have file count
                    if last_progress['total'] > 0:
                        current = int((percentage / 100) * last_progress['total'])
                        return (current, last_progress['total'], message)
                    else:
                        # No file count yet, use percentage as current with 100 as total
                        return (percentage, 100, message)
                
                return None
            
            # Read and print stdout in real-time (raw rclone output)
            def read_stdout():
                for line in iter(process.stdout.readline, ''):
                    if line:
                        line_stripped = line.rstrip()
                        stdout_lines.append(line)
                        
                        # Parse progress if callback provided
                        if progress_callback:
                            progress = parse_progress(line_stripped)
                            if progress:
                                current, total, message = progress
                                # Only update if progress changed (avoid spam)
                                if (current != last_progress['current'] or 
                                    total != last_progress['total'] or 
                                    message != last_progress['message']):
                                    last_progress['current'] = current
                                    last_progress['total'] = total
                                    last_progress['message'] = message
                                    try:
                                        progress_callback(current, total, message)
                                    except Exception:
                                        pass  # Don't fail on progress callback errors
                        
                        if line_stripped and not silent:
                            print(f"  {line_stripped}")
            
            # Start reading stdout in a thread to show raw output immediately
            stdout_thread = threading.Thread(target=read_stdout, daemon=True)
            stdout_thread.start()
            
            # Monitor log file for completion while process runs
            last_position = 0
            while process.poll() is None:
                # Check log file for completion indicators
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(last_position)
                        log_content = f.read()
                        last_position = f.tell()
                        
                        # Check for completion in log (rclone writes completion status to log)
                        if log_content:
                            # Look for common completion indicators in log
                            log_lower = log_content.lower()
                            if 'error' in log_lower or 'failed' in log_lower:
                                # Error detected in log, but let process finish naturally
                                pass
                except (IOError, OSError):
                    pass  # File might not be ready yet
                
                time.sleep(0.1)  # Small delay to avoid busy waiting
            
            # Wait for stdout reading thread to finish
            stdout_thread.join(timeout=2)
            
            # Read final log file content to check completion status
            log_content = ""
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    log_content = f.read()
            except (IOError, OSError):
                pass
            
            # Wait for process to finish
            process.wait(timeout=timeout)
            
            # Determine success from return code and log file
            success = process.returncode == 0
            
            # Combine stdout and log content
            all_output = ''.join(stdout_lines)
            if log_content and log_content not in all_output:
                all_output += log_content
            
            return success, all_output, ""
            
        except subprocess.TimeoutExpired:
            if 'process' in locals() and process:
                process.kill()
                process.wait()
            return False, ''.join(stdout_lines) if 'stdout_lines' in locals() else "", "Command timed out"
        except Exception as e:
            return False, "", str(e)
        finally:
            # Clean up log file
            if log_file and os.path.exists(log_file):
                try:
                    os.remove(log_file)
                except Exception:
                    pass
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize a path by converting backslashes to forward slashes and stripping
        Returns: Normalized path string
        """
        return path.replace('\\', '/').strip('/')
    
    def _build_remote_path(self, path: str) -> str:
        """
        Build full rclone remote path by prepending remote name
        
        Args:
            path: Path string (can be empty for root)
            
        Returns:
            Full remote path in format 'remote_name:path'
        """
        # Normalize the path
        normalized = self._normalize_path(path) if path else ''
        
        # Build full remote path: remote_name:path
        if normalized:
            return f"{self.remote_name}:{normalized}"
        else:
            return f"{self.remote_name}:"
    
    def _build_remote_path_with_index(self, username: Optional[str] = None, 
                                      game_name: Optional[str] = None, 
                                      folder_number: Optional[int] = None,
                                      remote_path_custom: Optional[str] = None,
                                      path_index: Optional[int] = None,
                                      additional_path: Optional[str] = None) -> str:
        """
        Build remote path with support for path_index subfolders
        
        Args:
            username: Username for path organization (required if remote_path_custom not provided)
            game_name: Game name for path organization (required if remote_path_custom not provided)
            folder_number: Save folder number (required if remote_path_custom not provided)
            remote_path_custom: Optional custom remote path (if provided, uses this as base - already includes path_index if needed)
            path_index: Optional path index (1-based) - only used if remote_path_custom is NOT provided
            additional_path: Optional additional path to append (e.g., filename)
        
        Returns:
            Normalized remote path string
        """
        if remote_path_custom:
            # Use custom path as base - it already includes path_index from backend
            remote_path = self._normalize_path(remote_path_custom)
            # Don't add path_index - it's already in remote_path_custom
        else:
            # Build path from components
            if not all([username, game_name, folder_number is not None]):
                raise ValueError("username, game_name, and folder_number required when remote_path_custom not provided")
            remote_path = self._get_full_path(username, game_name, folder_number, path_index=path_index)
        
        # Append additional path if provided (e.g., filename)
        if additional_path:
            additional_path = self._normalize_path(additional_path)
            remote_path = f"{remote_path}/{additional_path}"
        
        return remote_path
    
    def _parse_bytes_transferred(self, output: str) -> int:
        """Parse total bytes transferred from rclone output
        
        Looks for patterns like:
        - "Transferred: 0 B / 0 B" (empty)
        - "Transferred: 17.725 MiB / 17.725 MiB" (with data)
        - "Transferred: 1.234 KiB / 1.234 KiB"
        
        Returns:
            Total bytes transferred (0 if empty or not found)
        """
        if not output:
            return 0
        
        # Pattern: "Transferred: X.XXX Unit / Y.YYY Unit"
        # We want the second value (total transferred)
        pattern = r'Transferred:\s+[\d.]+\s+(\w+)\s+/\s+([\d.]+)\s+(\w+)'
        matches = re.findall(pattern, output)
        
        if not matches:
            # Try simpler pattern: "Transferred: 0 B / 0 B"
            simple_pattern = r'Transferred:\s+(\d+)\s+B\s+/\s+(\d+)\s+B'
            simple_matches = re.findall(simple_pattern, output)
            if simple_matches:
                # Return the second value (total)
                return int(simple_matches[-1][1])
            return 0
        
        # Get the last match (most recent stats)
        last_match = matches[-1]
        unit = last_match[2].upper()
        value = float(last_match[1])
        
        # Convert to bytes
        multipliers = {
            'B': 1,
            'KB': 1024,
            'KIB': 1024,
            'MB': 1024 * 1024,
            'MIB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024,
            'GIB': 1024 * 1024 * 1024,
        }
        
        multiplier = multipliers.get(unit, 1)
        return int(value * multiplier)
    
    def _parse_files_transferred(self, output: str) -> int:
        """Parse total files transferred from rclone output
        
        Looks for patterns like:
        - "Transferred: 1 / 1, 100%" (file count)
        - "Transferred: 5 / 10, 50%" (file count)
        
        This is different from bytes transferred - rclone shows both:
        - "Transferred: 0 B / 0 B" (bytes)
        - "Transferred: 1 / 1, 100%" (files)
        
        Returns:
            Total files transferred (0 if not found)
        """
        if not output:
            return 0
        
        # Pattern: "Transferred: X / Y, Z%" where X and Y are integers (file count)
        # This pattern appears when rclone shows file transfer count (not bytes)
        pattern = r'Transferred:\s+(\d+)\s+/\s+(\d+),?\s*\d*%?'
        matches = re.findall(pattern, output)
        
        if not matches:
            return 0
        
        # Get the last match (most recent stats) - return the first number (files transferred)
        # The second number is total files checked/processed
        last_match = matches[-1]
        files_transferred = int(last_match[0])
        return files_transferred
    
    def _get_full_path(self, username: str, game_name: str, folder_number: int, 
                      remote_path: str = '', path_index: Optional[int] = None) -> str:
        """Build full FTP path for save folder
        
        Args:
            username: Username for path organization
            game_name: Game name for path organization
            folder_number: Save folder number
            remote_path: Optional additional path suffix
            path_index: Optional path index (1-based) to create path_1, path_2 subfolders
        """
        safe_game_name = "".join(c for c in game_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_game_name = safe_game_name.replace(' ', '_')
        
        base_path = f"{username}/{safe_game_name}/save_{folder_number}"
        
        # Add path_index subfolder if provided
        if path_index is not None:
            base_path = f"{base_path}/path_{path_index}"
        
        if remote_path:
            # Normalize path separators
            remote_path = remote_path.replace('\\', '/').strip('/')
            full_path = f"{base_path}/{remote_path}"
        else:
            full_path = base_path
        
        return full_path
    
    def upload_directory(self, local_dir: str, username: str, game_name: str,
                        folder_number: int, remote_path_custom: Optional[str] = None,
                        path_index: Optional[int] = None,
                        transfers: int = 10, progress_callback: Optional[Callable[[int, int, str], None]] = None) -> Tuple[bool, str, List[str], List[dict], int, int]:
        """Upload entire directory - rclone handles everything with parallel transfers
        
        Args:
            local_dir: Local directory path
            username: Username for path organization
            game_name: Game name for path organization
            folder_number: Save folder number
            remote_path_custom: Optional custom remote path
            path_index: Optional path index (1-based) to create path_1, path_2 subfolders
            transfers: Number of parallel transfers (default: 10)
        
        Returns:
            Tuple of (success, message, uploaded_files, failed_files, bytes_transferred, files_transferred)
        """
        if not os.path.exists(local_dir):
            return False, f"Local directory not found: {local_dir}", [], [], 0, 0
        
        # Build remote path using helper
        remote_path = self._build_remote_path_with_index(
            username=username,
            game_name=game_name,
            folder_number=folder_number,
            remote_path_custom=remote_path_custom,
            path_index=path_index
        )
        remote_full = self._build_remote_path(remote_path)
        
        # Let rclone handle everything - parallel transfers, retries, resume
        # Note: rclone 'copy' command always overwrites existing files (default behavior)
        # This is desired for save games - we want the latest save to replace the old one
        command = [
            'copy',
            local_dir,
            remote_full,
            '--transfers', str(transfers),
            '--checkers', str(transfers * 2),  # More checkers for faster file discovery
            '--stats', '1s',  # Show stats every second
            '--progress',  # Show detailed progress for each file
            '--create-empty-src-dirs',  # Copy empty directories from source
        ]
        
        success, stdout, stderr = self._run_rclone(command, timeout=3600, progress_callback=progress_callback)
        
        # Parse bytes and files transferred from output
        bytes_transferred = self._parse_bytes_transferred(stdout)
        files_transferred = self._parse_files_transferred(stdout)
        
        if success:
            # Parse output to get file list (rclone doesn't provide this directly, but we can infer from stats)
            return True, "Directory uploaded successfully", [], [], bytes_transferred, files_transferred
        else:
            error_msg = stderr.strip() or stdout.strip() or "Upload failed"
            return False, error_msg, [], [], bytes_transferred, files_transferred
    
    def upload_save(self, username: str, game_name: str, local_file_path: str,
                   folder_number: int, remote_filename: Optional[str] = None,
                   remote_path_custom: Optional[str] = None, path_index: Optional[int] = None,
                   progress_callback: Optional[Callable[[int, int, str], None]] = None) -> Tuple[bool, str, int]:
        """Upload a save file - rclone handles everything (retries, resume, etc.)
        
        Args:
            username: Username for path organization
            game_name: Game name for path organization
            local_file_path: Local file path
            folder_number: Save folder number
            remote_filename: Remote filename (optional, defaults to basename)
            remote_path_custom: Optional custom remote path
            path_index: Optional path index (1-based) to create path_1, path_2 subfolders
        
        Returns:
            Tuple of (success, message, bytes_transferred)
        """
        if not os.path.exists(local_file_path):
            return False, f"Local file not found: {local_file_path}", 0
        
        if remote_filename is None:
            remote_filename = os.path.basename(local_file_path)
        
        # Build remote path using helper
        remote_path = self._build_remote_path_with_index(
            username=username,
            game_name=game_name,
            folder_number=folder_number,
            remote_path_custom=remote_path_custom,
            path_index=path_index,
            additional_path=remote_filename
        )
        remote_full = self._build_remote_path(remote_path)
        
        # Let rclone handle everything - retries, resume, connection management
        # Note: rclone 'copy' command always overwrites existing files (default behavior)
        # This is desired for save games - we want the latest save to replace the old one
        command = [
            'copy',
            local_file_path,
            remote_full,
            '--stats', '1s',  # Show stats every second
            '--progress',  # Show detailed progress
        ]
        
        success, stdout, stderr = self._run_rclone(command, timeout=600, progress_callback=progress_callback)
        
        # Parse bytes transferred from output
        bytes_transferred = self._parse_bytes_transferred(stdout)
        
        if success:
            return True, "File uploaded successfully", bytes_transferred
        else:
            error_msg = stderr.strip() or stdout.strip() or "Upload failed"
            return False, error_msg, bytes_transferred
    
    def download_save(self, username: str, game_name: str, remote_filename: str,
                     local_file_path: str, folder_number: int, 
                     remote_path_custom: Optional[str] = None, path_index: Optional[int] = None,
                     progress_callback: Optional[Callable[[int, int, str], None]] = None) -> Tuple[bool, str]:
        """Download a save file - rclone handles everything (retries, resume, etc.)
        
        Args:
            username: Username for path organization
            game_name: Game name for path organization
            remote_filename: Remote filename (relative path)
            local_file_path: Local file path
            folder_number: Save folder number
            remote_path_custom: Optional custom remote path
            path_index: Optional path index (1-based) to create path_1, path_2 subfolders
        
        Returns:
            Tuple of (success, message)
        """
        # Build remote path using helper
        remote_path = self._build_remote_path_with_index(
            username=username,
            game_name=game_name,
            folder_number=folder_number,
            remote_path_custom=remote_path_custom,
            path_index=path_index,
            additional_path=remote_filename
        )
        remote_full = self._build_remote_path(remote_path)
        
        # Create local directory if needed
        local_dir = os.path.dirname(local_file_path)
        if local_dir:
            try:
                os.makedirs(local_dir, exist_ok=True)
            except OSError as e:
                return False, f"Failed to create directory: {local_dir} - {str(e)}"
        
        # Let rclone handle everything - retries, resume, connection management
        # Note: rclone 'copy' command always overwrites existing files (default behavior)
        # This is desired for load operations - we want to replace local saves with server saves
        command = [
            'copy',
            remote_full,
            local_file_path,
            '--stats', '1s',  # Show stats every second
            '--progress',  # Show detailed progress
        ]
        
        success, stdout, stderr = self._run_rclone(command, timeout=600, progress_callback=progress_callback)
        
        if success:
            return True, "File downloaded successfully"
        else:
            error_msg = stderr.strip() or stdout.strip() or "Download failed"
            return False, error_msg
    
    def download_directory(self, remote_path_base: str, local_dir: str,
                          transfers: int = 10, progress_callback: Optional[Callable[[int, int, str], None]] = None) -> Tuple[bool, str, List[str], List[dict]]:
        """Download entire directory - rclone handles everything with parallel transfers
        
        Args:
            remote_path_base: Base remote path (e.g., "username/game/save_1")
            local_dir: Local directory path
            transfers: Number of parallel transfers (default: 10)
        
        Returns:
            Tuple of (success, message, downloaded_files, failed_files)
        """
        # Create local directory
        try:
            os.makedirs(local_dir, exist_ok=True)
        except OSError as e:
            return False, f"Failed to create directory: {local_dir} - {str(e)}", [], []
        
        remote_full = self._build_remote_path(remote_path_base)
        
        # Let rclone handle everything - parallel transfers, retries, resume
        # Note: rclone 'copy' command always overwrites existing files (default behavior)
        # This is desired for load operations - we want to replace local saves with server saves
        command = [
            'copy',
            remote_full,
            local_dir,
            '--transfers', str(transfers),
            '--checkers', str(transfers * 2),
            '--stats', '1s',  # Show stats every second
            '--progress',  # Show detailed progress for each file
            '--create-empty-src-dirs',  # Copy empty directories from source
        ]
        
        success, stdout, stderr = self._run_rclone(command, timeout=3600, progress_callback=progress_callback)
        
        if success:
            return True, "Directory downloaded successfully", [], []
        else:
            error_msg = stderr.strip() or stdout.strip() or "Download failed"
            return False, error_msg, [], []
    
    def list_saves(self, username: str, game_name: str, folder_number: int,
                  remote_path_custom: Optional[str] = None,
                  path_index: Optional[int] = None) -> Tuple[bool, List[dict], List[str], str]:
        """List all save files recursively via rclone
        
        Args:
            username: Username for path organization
            game_name: Game name for path organization
            folder_number: Save folder number
            remote_path_custom: Optional custom remote path
        
        Returns:
            Tuple of (success, files_list, directories_list, message)
        """
        # Build remote path using helper
        remote_path = self._build_remote_path_with_index(
            username=username,
            game_name=game_name,
            folder_number=folder_number,
            remote_path_custom=remote_path_custom,
            path_index=path_index
        )
        remote_full = self._build_remote_path(remote_path)
        
        # Use lsjson for structured output
        command = [
            'lsjson',
            remote_full,
            '--recursive',
        ]
        
        success, stdout, stderr = self._run_rclone(command, timeout=60)
        
        if not success:
            # Try without recursive to see if path exists
            check_cmd = ['lsjson', remote_full]
            check_success, _, _ = self._run_rclone(check_cmd, timeout=30)
            if not check_success:
                return False, [], [], f"Path not found: {remote_path}"
            return False, [], [], f"List failed: {stderr.strip() or 'Unknown error'}"
        
        # Parse JSON output
        try:
            items = json.loads(stdout) if stdout.strip() else []
        except json.JSONDecodeError:
            return False, [], [], "Failed to parse rclone output"
        
        files = []
        directories = set()
        base_path_len = len(remote_path) if remote_path else 0
        
        for item in items:
            full_path = item.get('Path', '').replace('\\', '/')
            
            # Get relative path (remove base path)
            if base_path_len > 0 and full_path.startswith(remote_path):
                rel_path = full_path[len(remote_path):].lstrip('/')
            else:
                rel_path = full_path
            
            if item.get('IsDir', False):
                if rel_path:
                    directories.add(rel_path)
            else:
                # File
                size = item.get('Size', 0)
                files.append({
                    'name': rel_path,
                    'size': size
                })
                # Also add parent directories
                dir_path = os.path.dirname(rel_path)
                while dir_path:
                    directories.add(dir_path)
                    dir_path = os.path.dirname(dir_path)
        
        directories = sorted(list(directories))
        
        return True, files, directories, f"Found {len(files)} file(s) and {len(directories)} directory(ies)"
    
    def create_directory(self, username: str, game_name: str, folder_number: int,
                        remote_dir_path: str, remote_path_custom: Optional[str] = None,
                        path_index: Optional[int] = None) -> Tuple[bool, str]:
        """Create directory - rclone handles everything
        
        Args:
            username: Username for path organization
            game_name: Game name for path organization
            folder_number: Save folder number
            remote_dir_path: Remote directory path (relative)
            remote_path_custom: Optional custom remote path
        
        Returns:
            Tuple of (success, message)
        """
        # Build remote path using helper
        remote_path = self._build_remote_path_with_index(
            username=username,
            game_name=game_name,
            folder_number=folder_number,
            remote_path_custom=remote_path_custom,
            path_index=path_index,
            additional_path=remote_dir_path
        )
        remote_full = self._build_remote_path(remote_path)
        
        # Let rclone handle it
        command = ['mkdir', remote_full]
        
        success, stdout, stderr = self._run_rclone(command, timeout=30)
        
        if success:
            return True, "Directory created"
        else:
            error_msg = stderr.strip().lower()
            if 'exists' in error_msg or 'already' in error_msg:
                return True, "Directory already exists"
            return False, stderr.strip() or "Failed to create directory"
    
    def delete_file(self, remote_path: str) -> Tuple[bool, str]:
        """Delete a file - rclone handles everything
        
        Args:
            remote_path: Full remote path (e.g., "username/game/save_1/file.txt")
        
        Returns:
            Tuple of (success, message)
        """
        remote_full = self._build_remote_path(remote_path)
        command = ['deletefile', remote_full]
        
        success, stdout, stderr = self._run_rclone(command, timeout=60)
        
        if success:
            return True, "File deleted"
        else:
            error_msg = stderr.strip() or stdout.strip() or "Delete failed"
            if 'not found' in error_msg.lower() or 'does not exist' in error_msg.lower():
                return True, "File already deleted"
            return False, error_msg
    
    def delete_directory(self, remote_path: str) -> Tuple[bool, str]:
        """
        Delete a directory recursively - rclone handles everything.
        
        Uses multiple methods to ensure complete deletion:
        1. First tries 'purge' to delete directory and all contents
        2. Then tries 'rmdir' to remove empty directory if it still exists
        3. This ensures empty folders are fully removed from FTP server
        
        Args:
            remote_path: Full remote path (e.g., "username/game/save_1")
        
        Returns:
            Tuple of (success, message)
        """
        remote_full = self._build_remote_path(remote_path)
        
        # Step 1: Try purge first (deletes directory and all contents)
        command = ['purge', remote_full]
        success, stdout, stderr = self._run_rclone(command, timeout=300, silent=True)
        
        if success:
            # Step 2: Try rmdir to ensure empty directory is removed (some FTP servers need this)
            # rmdir will fail if directory has contents, but succeed if it's empty or doesn't exist
            # This cleans up any empty folders that purge might have left behind
            rmdir_command = ['rmdir', remote_full]
            rmdir_success, rmdir_stdout, rmdir_stderr = self._run_rclone(rmdir_command, timeout=60, silent=True)
            
            # rmdir failure is OK if it's because directory doesn't exist or has contents
            # We only care if purge succeeded - rmdir is just cleanup
            return True, "Directory deleted"
        else:
            error_text = (stderr + stdout).lower()
            # Check for any variation of "not found" or "does not exist" errors
            not_found_patterns = [
                'not found',
                'does not exist',
                'directory not found',
                'file does not exist',
                'failed to list',
                'error listing'
            ]
            if any(pattern in error_text for pattern in not_found_patterns):
                # Directory doesn't exist - try rmdir anyway to clean up any empty parent dirs
                rmdir_command = ['rmdir', remote_full]
                self._run_rclone(rmdir_command, timeout=60, silent=True)
                return True, "Directory already deleted"
            
            # Not a "not found" error, show the actual output
            for line in stdout.split('\n'):
                if line.strip():
                    print(f"  {line.strip()}")
            error_msg = stderr.strip() or stdout.strip() or "Delete failed"
            return False, error_msg
    
    def check_status(self) -> Tuple[bool, str]:
        """
        Check rclone status by testing connection to remote
        
        Performs a quick test to verify:
        - rclone executable is accessible
        - Remote configuration is valid
        - Connection to remote server is working
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Test connection by listing root directory (quick operation)
            # Use a short timeout since this is just a status check
            remote_full = self._build_remote_path('')
            command = ['lsd', remote_full]
            
            success, stdout, stderr = self._run_rclone(command, timeout=10, silent=True)
            
            if success:
                return True, f"Rclone connected ({self.remote_name})"
            else:
                # Check if it's a connection error or just empty directory
                error_text = (stderr + stdout).lower()
                if 'connection' in error_text or 'timeout' in error_text or 'refused' in error_text:
                    return False, f"Rclone connection failed ({self.remote_name})"
                elif 'not found' in error_text or 'does not exist' in error_text:
                    # Directory doesn't exist but connection works
                    return True, f"Rclone connected ({self.remote_name})"
                else:
                    # Other error, but connection might still work
                    return True, f"Rclone connected ({self.remote_name})"
        except Exception as e:
            return False, f"Rclone status check failed: {str(e)}"

