"""
Rclone-based File Transfer Client for SaveNLoad
Uses rclone CLI for fast, reliable file transfers supporting multiple protocols
"""
import os
import subprocess
import json
import threading
from pathlib import Path
from typing import Optional, List, Tuple


class RcloneClient:
    """Rclone-based client for fast file transfers
    
    Supports: SMB, FTP, SFTP, and many other protocols via rclone
    """
    
    def __init__(self, remote_name: str = 'smb', rclone_path: Optional[str] = None, 
                 config_path: Optional[str] = None, share_name: Optional[str] = None):
        """Initialize rclone client
        
        Args:
            remote_name: Name of the rclone remote (from rclone.conf)
            rclone_path: Path to rclone executable (default: ./rclone/rclone.exe)
            config_path: Path to rclone config file (default: ./rclone/rclone.conf)
            share_name: SMB share name (if None, reads from SMB_SHARE env var)
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
        
        # Get share name from parameter or environment
        if share_name:
            self.share_name = share_name
        else:
            self.share_name = os.getenv('SMB_SHARE', 'n_Saves').strip()
        
        print(f"Rclone Client initialized")
        print(f"  Executable: {self.rclone_exe}")
        print(f"  Config: {self.config_path}")
        print(f"  Remote: {remote_name}")
        print(f"  Share: {self.share_name}")
    
    def _run_rclone(self, command: List[str], timeout: Optional[int] = None) -> Tuple[bool, str, str]:
        """Run rclone command and return success, stdout, stderr"""
        try:
            # Build full command with config
            full_cmd = [
                str(self.rclone_exe),
                '--config', str(self.config_path),
            ] + command
            
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            
            success = result.returncode == 0
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)
    
    def _build_remote_path(self, path: str) -> str:
        """Build remote path string for rclone with share name"""
        # Remove leading/trailing slashes and normalize
        path = path.replace('\\', '/').strip('/')
        # For SMB, path must include share name: smb:ShareName/path
        if path:
            return f"{self.remote_name}:{self.share_name}/{path}"
        else:
            return f"{self.remote_name}:{self.share_name}"
    
    def _get_full_path(self, username: str, game_name: str, folder_number: int, 
                      remote_path: str = '') -> str:
        """Build full SMB path for save folder (matching SMB client interface)"""
        safe_game_name = "".join(c for c in game_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_game_name = safe_game_name.replace(' ', '_')
        
        base_path = f"{username}/{safe_game_name}/save_{folder_number}"
        if remote_path:
            # Normalize path separators
            remote_path = remote_path.replace('\\', '/').strip('/')
            full_path = f"{base_path}/{remote_path}"
        else:
            full_path = base_path
        
        return full_path
    
    def upload_directory(self, local_dir: str, username: str, game_name: str,
                        folder_number: int, smb_path: Optional[str] = None,
                        transfers: int = 10) -> Tuple[bool, str, List[str], List[dict]]:
        """Upload entire directory - rclone handles everything with parallel transfers
        
        Args:
            local_dir: Local directory path
            username: Username for path organization
            game_name: Game name for path organization
            folder_number: Save folder number
            smb_path: Optional custom SMB path
            transfers: Number of parallel transfers (default: 10)
        
        Returns:
            Tuple of (success, message, uploaded_files, failed_files)
        """
        if not os.path.exists(local_dir):
            return False, f"Local directory not found: {local_dir}", [], []
        
        # Build remote path
        if smb_path:
            remote_path = smb_path.replace('\\', '/').strip('/')
        else:
            remote_path = self._get_full_path(username, game_name, folder_number)
        
        remote_full = self._build_remote_path(remote_path)
        
        # Let rclone handle everything - parallel transfers, retries, resume
        command = [
            'copy',
            local_dir,
            remote_full,
            '--transfers', str(transfers),
            '--checkers', str(transfers * 2),  # More checkers for faster file discovery
            '--stats', '1s',  # Show stats every second
            '--progress',  # Show progress
        ]
        
        success, stdout, stderr = self._run_rclone(command, timeout=3600)
        
        if success:
            # Parse output to get file list (rclone doesn't provide this directly, but we can infer from stats)
            return True, "Directory uploaded successfully", [], []
        else:
            error_msg = stderr.strip() or stdout.strip() or "Upload failed"
            return False, error_msg, [], []
    
    def upload_save(self, username: str, game_name: str, local_file_path: str,
                   folder_number: int, remote_filename: Optional[str] = None,
                   smb_path: Optional[str] = None) -> Tuple[bool, str]:
        """Upload a save file - rclone handles everything (retries, resume, etc.)
        
        Args:
            username: Username for path organization
            game_name: Game name for path organization
            local_file_path: Local file path
            folder_number: Save folder number
            remote_filename: Remote filename (optional, defaults to basename)
            smb_path: Optional custom SMB path
        
        Returns:
            Tuple of (success, message)
        """
        if not os.path.exists(local_file_path):
            return False, f"Local file not found: {local_file_path}"
        
        if remote_filename is None:
            remote_filename = os.path.basename(local_file_path)
        
        # Build remote path
        if smb_path:
            remote_path = smb_path.replace('\\', '/').strip('/')
            if remote_filename:
                remote_path = f"{remote_path}/{remote_filename}"
        else:
            base_path = self._get_full_path(username, game_name, folder_number)
            remote_path = f"{base_path}/{remote_filename}"
        
        remote_full = self._build_remote_path(remote_path)
        
        # Let rclone handle everything - retries, resume, connection management
        command = [
            'copy',
            local_file_path,
            remote_full,
        ]
        
        success, stdout, stderr = self._run_rclone(command, timeout=600)
        
        if success:
            return True, "File uploaded successfully"
        else:
            error_msg = stderr.strip() or stdout.strip() or "Upload failed"
            return False, error_msg
    
    def download_save(self, username: str, game_name: str, remote_filename: str,
                     local_file_path: str, folder_number: int, 
                     smb_path: Optional[str] = None) -> Tuple[bool, str]:
        """Download a save file - rclone handles everything (retries, resume, etc.)
        
        Args:
            username: Username for path organization
            game_name: Game name for path organization
            remote_filename: Remote filename (relative path)
            local_file_path: Local file path
            folder_number: Save folder number
            smb_path: Optional custom SMB path
        
        Returns:
            Tuple of (success, message)
        """
        # Build remote path
        if smb_path:
            remote_path = smb_path.replace('\\', '/').strip('/')
            if remote_filename:
                remote_path = f"{remote_path}/{remote_filename}"
        else:
            base_path = self._get_full_path(username, game_name, folder_number)
            remote_path = f"{base_path}/{remote_filename}"
        
        remote_full = self._build_remote_path(remote_path)
        
        # Create local directory if needed
        local_dir = os.path.dirname(local_file_path)
        if local_dir:
            try:
                os.makedirs(local_dir, exist_ok=True)
            except OSError as e:
                return False, f"Failed to create directory: {local_dir} - {str(e)}"
        
        # Let rclone handle everything - retries, resume, connection management
        command = [
            'copy',
            remote_full,
            local_file_path,
        ]
        
        success, stdout, stderr = self._run_rclone(command, timeout=600)
        
        if success:
            return True, "File downloaded successfully"
        else:
            error_msg = stderr.strip() or stdout.strip() or "Download failed"
            return False, error_msg
    
    def download_directory(self, remote_path_base: str, local_dir: str,
                          transfers: int = 10) -> Tuple[bool, str, List[str], List[dict]]:
        """Download entire directory - rclone handles everything with parallel transfers
        
        Args:
            remote_path_base: Base remote path (e.g., "username/game/save_1")
            local_dir: Local directory path
            transfers: Number of parallel transfers (default: 10)
        
        Returns:
            Tuple of (success, message, downloaded_files, failed_files)
        """
        # Create local directory if needed
        try:
            os.makedirs(local_dir, exist_ok=True)
        except OSError as e:
            return False, f"Failed to create directory: {local_dir} - {str(e)}", [], []
        
        remote_full = self._build_remote_path(remote_path_base)
        
        # Let rclone handle everything - parallel transfers, retries, resume
        command = [
            'copy',
            remote_full,
            local_dir,
            '--transfers', str(transfers),
            '--checkers', str(transfers * 2),
            '--stats', '1s',
            '--progress',
        ]
        
        success, stdout, stderr = self._run_rclone(command, timeout=3600)
        
        if success:
            return True, "Directory downloaded successfully", [], []
        else:
            error_msg = stderr.strip() or stdout.strip() or "Download failed"
            return False, error_msg, [], []
    
    def list_saves(self, username: str, game_name: str, folder_number: int,
                  smb_path: Optional[str] = None) -> Tuple[bool, List[dict], List[str], str]:
        """List all save files recursively via rclone (matching SMB client interface)
        
        Args:
            username: Username for path organization
            game_name: Game name for path organization
            folder_number: Save folder number
            smb_path: Optional custom SMB path
        
        Returns:
            Tuple of (success, files_list, directories_list, message)
        """
        # Build remote path
        if smb_path:
            remote_path = smb_path.replace('\\', '/').strip('/')
        else:
            remote_path = self._get_full_path(username, game_name, folder_number)
        
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
                        remote_dir_path: str, smb_path: Optional[str] = None) -> Tuple[bool, str]:
        """Create directory - rclone handles everything
        
        Args:
            username: Username for path organization
            game_name: Game name for path organization
            folder_number: Save folder number
            remote_dir_path: Remote directory path (relative)
            smb_path: Optional custom SMB path
        
        Returns:
            Tuple of (success, message)
        """
        # Build remote path
        if smb_path:
            base_path = smb_path.replace('\\', '/').strip('/')
        else:
            base_path = self._get_full_path(username, game_name, folder_number)
        
        if remote_dir_path:
            remote_dir_path = remote_dir_path.replace('\\', '/').strip('/')
            remote_path = f"{base_path}/{remote_dir_path}"
        else:
            remote_path = base_path
        
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
    
    def delete_file(self, smb_path: str) -> Tuple[bool, str]:
        """Delete a file - rclone handles everything
        
        Args:
            smb_path: Full SMB path (e.g., "username/game/save_1/file.txt")
        
        Returns:
            Tuple of (success, message)
        """
        remote_full = self._build_remote_path(smb_path)
        command = ['deletefile', remote_full]
        
        success, stdout, stderr = self._run_rclone(command, timeout=60)
        
        if success:
            return True, "File deleted"
        else:
            error_msg = stderr.strip() or stdout.strip() or "Delete failed"
            if 'not found' in error_msg.lower() or 'does not exist' in error_msg.lower():
                return True, "File already deleted"
            return False, error_msg
    
    def delete_directory(self, smb_path: str) -> Tuple[bool, str]:
        """Delete a directory recursively - rclone handles everything
        
        Args:
            smb_path: Full SMB path (e.g., "username/game/save_1")
        
        Returns:
            Tuple of (success, message)
        """
        remote_full = self._build_remote_path(smb_path)
        command = ['purge', remote_full]
        
        success, stdout, stderr = self._run_rclone(command, timeout=300)
        
        if success:
            return True, "Directory deleted"
        else:
            error_msg = stderr.strip() or stdout.strip() or "Delete failed"
            if 'not found' in error_msg.lower() or 'does not exist' in error_msg.lower():
                return True, "Directory already deleted"
            return False, error_msg

