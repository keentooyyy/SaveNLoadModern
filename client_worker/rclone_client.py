"""
Rclone-based File Transfer Client for SaveNLoad
Uses rclone rc API for fast, reliable file transfers supporting multiple protocols
"""
import os
import subprocess
import threading
import time
import atexit
import requests
from pathlib import Path
from typing import Optional, List, Tuple, Callable, Dict, Any

# Rclone configuration constants
# Number of parallel file transfers for rclone operations
RCLONE_TRANSFERS = 10
RCLONE_RC_HOST = "127.0.0.1"
RCLONE_RC_PORT = 5572


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

        Returns:
            None
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
        self._rc_url = f"http://{RCLONE_RC_HOST}:{RCLONE_RC_PORT}"
        self._rcd_process = None
        self._rcd_owned = False
        self._rc_ready = False
        self._rc_lock = threading.Lock()
        self._rc_last_error = None

        atexit.register(self._shutdown_rcd)

    def _shutdown_rcd(self):
        """Shutdown rclone rcd if this instance started it."""
        if not self._rcd_owned or not self._rcd_process:
            return
        try:
            if self._rc_ready:
                self._rc_post("core/quit", {"exitCode": 0}, timeout=2)
        except Exception:
            pass
        try:
            if self._rcd_process.poll() is None:
                self._rcd_process.terminate()
        except Exception:
            pass

    def _rc_post(self, command: str, params: Dict[str, Any], timeout: Optional[int] = None) -> Tuple[bool, Dict[str, Any], str]:
        """Send a POST to the rclone rc endpoint."""
        url = f"{self._rc_url}/{command.lstrip('/')}"
        try:
            response = requests.post(url, json=params or {}, timeout=timeout or 30)
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    return False, {}, error_data.get("error", f"RC error {response.status_code}")
                except Exception:
                    return False, {}, f"RC error {response.status_code}: {response.text}"
            if not response.text:
                return True, {}, ""
            return True, response.json(), ""
        except Exception as e:
            return False, {}, str(e)

    def _rc_ping(self) -> bool:
        """Check if the rc endpoint is alive."""
        success, _, _ = self._rc_post("rc/noop", {}, timeout=2)
        return success

    def _ensure_rcd(self) -> bool:
        """Ensure rclone rcd is running and reachable."""
        if self._rc_ready:
            return True

        with self._rc_lock:
            if self._rc_ready:
                return True

            if self._rc_ping():
                self._rc_ready = True
                return True

            if self._rcd_process and self._rcd_process.poll() is None:
                if self._rc_ping():
                    self._rc_ready = True
                    return True

            command = [
                str(self.rclone_exe),
                'rcd',
                '--config', str(self.config_path),
                '--rc-addr', f"{RCLONE_RC_HOST}:{RCLONE_RC_PORT}",
                '--rc-no-auth',
            ]
            try:
                self._rcd_process = subprocess.Popen(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self._rcd_owned = True
            except Exception as e:
                self._rc_last_error = f"Failed to start rclone rcd: {e}"
                return False

            for _ in range(50):
                if self._rc_ping():
                    self._rc_ready = True
                    return True
                time.sleep(0.1)

            self._rc_last_error = "Timed out waiting for rclone rcd to start"
            return False

    def _rc_call(self, command: str, params: Dict[str, Any], timeout: Optional[int] = None) -> Tuple[bool, Dict[str, Any], str]:
        """Call an rclone rc command."""
        if not self._ensure_rcd():
            error = self._rc_last_error or "RC server is not available"
            return False, {}, error
        return self._rc_post(command, params, timeout=timeout)

    def _format_bytes(self, value: float) -> str:
        """Format bytes into a human-readable string."""
        units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
        size = float(value)
        for unit in units:
            if size < 1024 or unit == units[-1]:
                return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
            size /= 1024
        return f"{int(value)} B"

    def _build_progress(self, stats: Dict[str, Any]) -> Tuple[int, int, str]:
        """Convert rc stats to a progress tuple."""
        transfers = int(stats.get("transfers") or 0)
        total_transfers = int(stats.get("totalTransfers") or 0)
        bytes_done = int(stats.get("bytes") or 0)
        total_bytes = int(stats.get("totalBytes") or 0)
        speed = float(stats.get("speed") or 0)

        if total_transfers > 0:
            percent = int((transfers / total_transfers) * 100) if total_transfers else 0
            message = f"{percent}% - {transfers}/{total_transfers} files"
            if speed:
                message += f" @ {self._format_bytes(speed)}/s"
            return transfers, total_transfers, message

        if total_bytes > 0:
            percent = int((bytes_done / total_bytes) * 100) if total_bytes else 0
            message = f"{percent}% - {self._format_bytes(bytes_done)}/{self._format_bytes(total_bytes)}"
            if speed:
                message += f" @ {self._format_bytes(speed)}/s"
            return bytes_done, total_bytes, message

        message = f"{transfers} files"
        if speed:
            message += f" @ {self._format_bytes(speed)}/s"
        return transfers, total_transfers, message

    def _run_rc_job(self, command: str, params: Dict[str, Any], timeout: Optional[int],
                    progress_callback: Optional[Callable[[int, int, str], None]] = None) -> Tuple[bool, str, Dict[str, Any]]:
        """Run an rc command as an async job and poll for completion."""
        payload = dict(params or {})
        payload["_async"] = True

        success, data, error = self._rc_call(command, payload, timeout=10)
        if not success:
            return False, error, {}

        job_id = data.get("jobid")
        if job_id is None:
            return False, "RC did not return a job id", {}

        group_name = f"job/{job_id}"
        start_time = time.time()
        last_progress = {"current": None, "total": None, "message": None}
        last_stats: Dict[str, Any] = {}

        while True:
            status_success, status_data, status_error = self._rc_call("job/status", {"jobid": job_id}, timeout=10)
            if not status_success:
                return False, status_error, last_stats

            stats_success, stats_data, _ = self._rc_call("core/stats", {"group": group_name, "short": True}, timeout=10)
            if stats_success:
                last_stats = stats_data
                if progress_callback:
                    current, total, message = self._build_progress(stats_data)
                    if (current != last_progress["current"] or
                        total != last_progress["total"] or
                        message != last_progress["message"]):
                        last_progress["current"] = current
                        last_progress["total"] = total
                        last_progress["message"] = message
                        try:
                            progress_callback(current, total, message)
                        except Exception:
                            pass

            if status_data.get("finished"):
                error_text = status_data.get("error") or ""
                success_flag = bool(status_data.get("success"))
                try:
                    self._rc_call("core/stats-delete", {"group": group_name}, timeout=5)
                except Exception:
                    pass
                return success_flag, error_text, last_stats

            if timeout is not None and (time.time() - start_time) > timeout:
                return False, "Command timed out", last_stats

            time.sleep(0.2)

    def _split_local_path(self, path: str) -> Tuple[str, str]:
        """Split a local path into (fs, remote) for rc file operations."""
        path_obj = Path(path).resolve()
        anchor = path_obj.anchor or os.sep
        try:
            relative = path_obj.relative_to(anchor).as_posix()
        except ValueError:
            relative = path_obj.name
        return anchor, relative

    def _rc_list(self, remote_path: str) -> Tuple[bool, List[Dict[str, Any]], str]:
        """List a remote path using rc operations/list."""
        params = {
            "fs": f"{self.remote_name}:",
            "remote": remote_path,
            "opt": {"recurse": True},
        }
        success, data, error = self._rc_call("operations/list", params, timeout=60)
        if not success:
            return False, [], error
        return True, data.get("list", []) or [], ""
    
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize a path by converting backslashes to forward slashes and stripping.

        Args:
            path: Path string to normalize.

        Returns:
            Normalized path string.
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
    
    
    def upload_directory(self, local_dir: str, remote_ftp_path: str,
                        transfers: int = RCLONE_TRANSFERS, progress_callback: Optional[Callable[[int, int, str], None]] = None) -> Tuple[bool, str, List[str], List[dict], int, int]:
        """
        Upload directory to remote FTP path
        
        Args:
            local_dir: Local directory to upload
            remote_ftp_path: Complete remote FTP path (e.g., "username/GameName/save_1/path_2")
            transfers: Number of parallel transfers
            progress_callback: Optional progress callback
        
        Returns:
            Tuple of (success, message, uploaded_files, failed_files, bytes_transferred, files_transferred)
        """
        if not os.path.exists(local_dir):
            return False, f"Local directory not found: {local_dir}", [], [], 0, 0
        
        # Normalize and build full remote path with remote name prefix
        normalized_path = self._normalize_path(remote_ftp_path)
        remote_full = self._build_remote_path(normalized_path)
        
        # Use rc API for progress and stats.
        rc_success, rc_error, rc_stats = self._run_rc_job(
            "sync/copy",
            {
                "srcFs": local_dir,
                "dstFs": remote_full,
                "createEmptySrcDirs": True,
                "_config": {
                    "Transfers": transfers,
                    "Checkers": transfers * 2,
                }
            },
            timeout=3600,
            progress_callback=progress_callback
        )

        if rc_success:
            bytes_transferred = int(rc_stats.get("bytes") or 0)
            files_transferred = int(rc_stats.get("transfers") or 0)
            return True, "Directory uploaded successfully", [], [], bytes_transferred, files_transferred
        
        error_msg = rc_error or "Upload failed"
        return False, error_msg, [], [], 0, 0
    
    def upload_save(self, local_file_path: str, remote_ftp_path: str,
                   remote_filename: Optional[str] = None,
                   progress_callback: Optional[Callable[[int, int, str], None]] = None) -> Tuple[bool, str, int]:
        """
        Upload a save file to remote FTP path
        
        Args:
            local_file_path: Local file path
            remote_ftp_path: Complete remote FTP path (e.g., "username/GameName/save_1")
            remote_filename: Remote filename (optional, defaults to basename)
            progress_callback: Optional progress callback
        
        Returns:
            Tuple of (success, message, bytes_transferred)
        """
        if not os.path.exists(local_file_path):
            return False, f"Local file not found: {local_file_path}", 0
        
        if remote_filename is None:
            remote_filename = os.path.basename(local_file_path)
        
        # Build complete remote path with filename
        normalized_path = self._normalize_path(remote_ftp_path)
        remote_path_with_file = f"{normalized_path}/{remote_filename}"
        # Use rc API for progress and stats.
        src_fs, src_remote = self._split_local_path(local_file_path)
        dst_fs = f"{self.remote_name}:"
        dst_remote = self._normalize_path(remote_path_with_file)

        rc_success, rc_error, rc_stats = self._run_rc_job(
            "operations/copyfile",
            {
                "srcFs": src_fs,
                "srcRemote": src_remote,
                "dstFs": dst_fs,
                "dstRemote": dst_remote,
            },
            timeout=600,
            progress_callback=progress_callback
        )

        if rc_success:
            bytes_transferred = int(rc_stats.get("bytes") or 0)
            return True, "File uploaded successfully", bytes_transferred
        
        error_msg = rc_error or "Upload failed"
        return False, error_msg, 0
    
    
    def download_directory(self, remote_ftp_path: str, local_dir: str,
                          transfers: int = RCLONE_TRANSFERS, progress_callback: Optional[Callable[[int, int, str], None]] = None,
                          strip_path_prefix: Optional[str] = None) -> Tuple[bool, str, List[str], List[dict]]:
        """
        Download directory from remote FTP path
        
        Args:
            remote_ftp_path: Complete remote FTP path (e.g., "username/game/save_1" or "username/game/save_1/path_1")
            local_dir: Local directory path
            transfers: Number of parallel transfers (default: 10)
            progress_callback: Optional callback(current, total, message) for progress updates
            strip_path_prefix: Optional path prefix to strip from source (e.g., "path_1" to avoid creating path_1 subfolder)
        
        Returns:
            Tuple of (success, message, downloaded_files, failed_files)
        """
        # Create local directory
        try:
            os.makedirs(local_dir, exist_ok=True)
        except OSError as e:
            return False, f"Failed to create directory: {local_dir} - {str(e)}", [], []
        
        # Normalize and build full remote path
        base_path = self._normalize_path(remote_ftp_path)
        remote_full = self._build_remote_path(base_path)
        
        # If we need to strip path_X prefix, use temp directory workaround.
        if strip_path_prefix:
            # PROBLEM: Wildcard /* doesn't work with FTP servers
            # SOLUTION: Copy to temp directory, then move contents to final destination
            # strip_path_prefix is already in format "path_1", "path_2", etc.
            
            # Create temp directory in parent of local_dir to avoid conflicts
            import tempfile
            temp_parent = os.path.dirname(local_dir) or os.getcwd()
            temp_dir = tempfile.mkdtemp(prefix='rclone_path_', dir=temp_parent)
            
            try:
                # Copy directory directly (no wildcard) - this will create path_X subfolder in temp
                rc_success, rc_error, _ = self._run_rc_job(
                    "sync/copy",
                    {
                        "srcFs": remote_full,
                        "dstFs": temp_dir,
                        "createEmptySrcDirs": True,
                        "_config": {
                            "Transfers": transfers,
                            "Checkers": transfers * 2,
                        }
                    },
                    timeout=3600,
                    progress_callback=progress_callback
                )
                
                if not rc_success:
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    error_msg = rc_error or "Download failed"
                    return False, error_msg, [], []
                
                # Step 2: Move files from temp/path_X/ to local_dir/
                # strip_path_prefix is already "path_1", "path_2", etc. - use it directly
                path_x_dir = os.path.join(temp_dir, strip_path_prefix)
                
                if os.path.exists(path_x_dir) and os.path.isdir(path_x_dir):
                    import shutil
                    # Move all contents from path_X subfolder to final destination
                    moved_count = 0
                    for item in os.listdir(path_x_dir):
                        src = os.path.join(path_x_dir, item)
                        dst = os.path.join(local_dir, item)
                        
                        try:
                            if os.path.isdir(src):
                                # Directory: remove destination if exists, then move
                                if os.path.exists(dst):
                                    shutil.rmtree(dst)
                                shutil.move(src, dst)
                            else:
                                # File: remove destination if exists, then move
                                if os.path.exists(dst):
                                    os.remove(dst)
                                shutil.move(src, dst)
                            moved_count += 1
                        except Exception as e:
                            print(f"Warning: Failed to move {item}: {str(e)}")
                    
                    # Clean up temp directory
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    
                    return True, f"Directory downloaded successfully ({moved_count} items)", [], []
                else:
                    # Files might be directly in temp_dir (rclone copied contents, not directory)
                    # This can happen with some FTP servers
                    if os.path.exists(temp_dir):
                        items = os.listdir(temp_dir)
                        if items:
                            import shutil
                            moved_count = 0
                            for item in items:
                                src = os.path.join(temp_dir, item)
                                dst = os.path.join(local_dir, item)
                                try:
                                    if os.path.exists(dst):
                                        if os.path.isdir(dst):
                                            shutil.rmtree(dst)
                                        else:
                                            os.remove(dst)
                                    shutil.move(src, dst)
                                    moved_count += 1
                                except Exception as e:
                                    print(f"Warning: Failed to move {item}: {str(e)}")
                            
                            shutil.rmtree(temp_dir, ignore_errors=True)
                            return True, f"Directory downloaded successfully ({moved_count} items)", [], []
                    
                    # Clean up and return error
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return False, f"Unexpected directory structure after copy - expected {path_x_dir} or files in {temp_dir}", [], []
                    
            except Exception as e:
                # Clean up temp directory on any error
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False, f"Error during multi-path copy: {str(e)}", [], []
        else:
            # Normal copy for single paths
            rc_success, rc_error, _ = self._run_rc_job(
                "sync/copy",
                {
                    "srcFs": remote_full,
                    "dstFs": local_dir,
                    "createEmptySrcDirs": True,
                    "_config": {
                        "Transfers": transfers,
                        "Checkers": transfers * 2,
                    }
                },
                timeout=3600,
                progress_callback=progress_callback
            )
            
            if rc_success:
                return True, "Directory downloaded successfully", [], []
            else:
                error_msg = rc_error or "Download failed"
                return False, error_msg, [], []
    
    def list_saves(self, remote_ftp_path: str) -> Tuple[bool, List[dict], List[str], str]:
        """
        List all save files from remote FTP path
        
        Args:
            remote_ftp_path: Complete remote FTP path (e.g., "username/GameName/save_1")
        
        Returns:
            Tuple of (success, files_list, directories_list, message)
        """
        # Normalize remote path
        base_path = self._normalize_path(remote_ftp_path)
        
        rc_success, rc_items, rc_error = self._rc_list(base_path)
        if not rc_success:
            error_msg = rc_error or f"Path not found: {base_path}"
            return False, [], [], error_msg
        items = rc_items
        
        files = []
        directories = set()
        base_path_len = len(base_path) if base_path else 0
        
        for item in items:
            full_path = item.get('Path', '').replace('\\', '/')
            
            # Get relative path (remove base path)
            if base_path_len > 0 and full_path.startswith(base_path):
                rel_path = full_path[len(base_path):].lstrip('/')
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
    
    
    def delete_file(self, remote_path: str) -> Tuple[bool, str]:
        """Delete a file - rclone handles everything
        
        Args:
            remote_path: Full remote path (e.g., "username/game/save_1/file.txt")
        
        Returns:
            Tuple of (success, message)
        """
        normalized_path = self._normalize_path(remote_path)
        rc_success, _, rc_error = self._rc_call(
            "operations/deletefile",
            {"fs": f"{self.remote_name}:", "remote": normalized_path},
            timeout=60
        )
        
        if rc_success:
            return True, "File deleted"
        error_msg = rc_error or "Delete failed"
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
        normalized_path = self._normalize_path(remote_path)
        
        rc_success, rc_error, _ = self._run_rc_job(
            "operations/purge",
            {"fs": f"{self.remote_name}:", "remote": normalized_path},
            timeout=300
        )
        
        if rc_success:
            self._rc_call("operations/rmdir", {"fs": f"{self.remote_name}:", "remote": normalized_path}, timeout=60)
            return True, "Directory deleted"
        
        error_text = (rc_error or "").lower()
        not_found_patterns = [
            'not found',
            'does not exist',
            'directory not found',
            'file does not exist',
            'failed to list',
            'error listing'
        ]
        if any(pattern in error_text for pattern in not_found_patterns):
            self._rc_call("operations/rmdir", {"fs": f"{self.remote_name}:", "remote": normalized_path}, timeout=60)
            return True, "Directory already deleted"
        error_msg = rc_error or "Delete failed"
        return False, error_msg
    
    def check_status(self) -> Tuple[bool, str]:
        """
        Check rclone status by testing connection to remote
        
        Performs a quick test to verify:
        - rclone executable is accessible
        - Remote configuration is valid
        - Connection to remote server is working
        
        Args:
            None

        Returns:
            Tuple of (success, message)
        """
        try:
            rc_success, _, rc_error = self._rc_call(
                "operations/fsinfo",
                {"fs": f"{self.remote_name}:"},
                timeout=10
            )
            if rc_success:
                return True, f"Rclone connected ({self.remote_name})"
            return False, rc_error or f"Rclone connection failed ({self.remote_name})"
        except Exception as e:
            return False, f"Rclone status check failed: {str(e)}"

