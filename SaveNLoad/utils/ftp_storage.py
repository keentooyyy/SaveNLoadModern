"""
FTP Storage Utility for Django Backend
FTP storage backend using rclone for file operations
"""
import os
import io
import zipfile
import logging
import subprocess
import json
import tempfile
import shutil
from pathlib import Path
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class FTPStorage:
    """FTP storage backend for save files using rclone
    
    Uses rclone for fast, reliable FTP file operations
    """
    
    def __init__(self):
        """Initialize FTP storage with credentials from environment"""
        self.host = os.getenv('FTP_HOST')
        self.username = os.getenv('FTP_USERNAME')
        self.password = os.getenv('FTP_PASSWORD')
        
        if not all([self.host, self.username, self.password]):
            raise ValueError("FTP credentials must be set in environment variables (FTP_HOST, FTP_USERNAME, FTP_PASSWORD)")
        
        # Find rclone executable
        script_dir = Path(__file__).parent.parent.parent / 'client_worker'
        self.rclone_exe = script_dir / 'rclone' / 'rclone.exe'
        self.config_path = script_dir / 'rclone' / 'rclone.conf'
        
        if not self.rclone_exe.exists():
            raise ValueError(f"rclone executable not found at: {self.rclone_exe}")
        if not self.config_path.exists():
            raise ValueError(f"rclone config not found at: {self.config_path}")
        
        logger.info(f"FTP Storage initialized: {self.host}")
    
    def _run_rclone(self, command: List[str], timeout: Optional[int] = None) -> Tuple[bool, str]:
        """Run rclone command and return success, output"""
        try:
            full_cmd = [
                str(self.rclone_exe),
                '--config', str(self.config_path),
            ] + command
            
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            logger.error(f"rclone command failed: {e}")
            return False, str(e)
    
    def _build_remote_path(self, ftp_path: str) -> str:
        """Convert FTP path to full rclone path"""
        # Normalize path
        normalized = ftp_path.lstrip('/').replace('\\', '/')
        return f"ftp:/{normalized}"
    
    def path_exists(self, ftp_path: str) -> bool:
        """Check if path exists on FTP server"""
        try:
            remote_full = self._build_remote_path(ftp_path)
            success, _ = self._run_rclone(['ls', remote_full], timeout=30)
            return success
        except Exception as e:
            logger.error(f"FTP path_exists failed for {ftp_path}: {e}")
            return False
    
    def is_directory(self, ftp_path: str) -> bool:
        """Check if path is a directory"""
        try:
            remote_full = self._build_remote_path(ftp_path)
            success, output = self._run_rclone(['lsjson', remote_full], timeout=30)
            if success:
                items = json.loads(output) if output.strip() else []
                return any(item.get('IsDir', False) for item in items if isinstance(items, list))
            return False
        except Exception as e:
            logger.error(f"FTP is_directory failed for {ftp_path}: {e}")
            return False
    
    def list_directory(self, ftp_path: str) -> Tuple[List[str], List[str]]:
        """List directory contents
        
        Returns:
            Tuple of (files_list, directories_list)
        """
        try:
            remote_full = self._build_remote_path(ftp_path)
            success, output = self._run_rclone(['lsjson', remote_full], timeout=60)
            
            if not success:
                return [], []
            
            files = []
            directories = []
            
            try:
                items = json.loads(output) if output.strip() else []
                if not isinstance(items, list):
                    items = []
                
                for item in items:
                    name = item.get('Path', '').split('/')[-1]  # Get just filename
                    if item.get('IsDir', False):
                        directories.append(name)
                    else:
                        files.append(name)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse rclone JSON output for {ftp_path}")
                return [], []
            
            return files, directories
        except Exception as e:
            logger.error(f"FTP list_directory failed for {ftp_path}: {e}")
            return [], []
    
    def list_recursive(self, ftp_path: str) -> Tuple[List[dict], List[str]]:
        """List all files recursively
        
        Returns:
            Tuple of (files_list with metadata, directories_list)
        """
        try:
            remote_full = self._build_remote_path(ftp_path)
            success, output = self._run_rclone(['lsjson', remote_full, '--recursive'], timeout=300)
            
            if not success:
                return [], []
            
            files = []
            directories = set()
            base_path_len = len(ftp_path) if ftp_path else 0
            
            try:
                items = json.loads(output) if output.strip() else []
                if not isinstance(items, list):
                    items = []
                
                for item in items:
                    full_path = item.get('Path', '').replace('\\', '/')
                    
                    # Get relative path
                    if base_path_len > 0 and full_path.startswith(ftp_path):
                        rel_path = full_path[len(ftp_path):].lstrip('/')
                    else:
                        rel_path = full_path
                    
                    if item.get('IsDir', False):
                        if rel_path:
                            directories.add(rel_path)
                    else:
                        files.append({
                            'name': rel_path,
                            'size': item.get('Size', 0)
                        })
                        # Add parent directories
                        dir_path = os.path.dirname(rel_path)
                        while dir_path:
                            directories.add(dir_path)
                            dir_path = os.path.dirname(dir_path)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse rclone JSON output for {ftp_path}")
                return [], []
            
            return files, sorted(list(directories))
        except Exception as e:
            logger.error(f"FTP list_recursive failed for {ftp_path}: {e}")
            return [], []
    
    def create_directory(self, ftp_path: str) -> bool:
        """Create directory structure (creates parent directories if needed)"""
        try:
            remote_full = self._build_remote_path(ftp_path)
            success, _ = self._run_rclone(['mkdir', remote_full], timeout=30)
            return success
        except Exception as e:
            logger.error(f"FTP create_directory failed for {ftp_path}: {e}")
            return False
    
    def delete_file(self, ftp_path: str) -> bool:
        """Delete a file"""
        try:
            remote_full = self._build_remote_path(ftp_path)
            success, _ = self._run_rclone(['deletefile', remote_full], timeout=60)
            return success
        except Exception as e:
            logger.error(f"FTP delete_file failed for {ftp_path}: {e}")
            return False
    
    def delete_directory(self, ftp_path: str, recursive: bool = True) -> bool:
        """Delete a directory
        
        Args:
            ftp_path: Path to directory
            recursive: If True, delete all contents recursively
        """
        try:
            remote_full = self._build_remote_path(ftp_path)
            if recursive:
                success, _ = self._run_rclone(['purge', remote_full], timeout=300)
            else:
                success, _ = self._run_rclone(['rmdir', remote_full], timeout=60)
            return success
        except Exception as e:
            logger.error(f"FTP delete_directory failed for {ftp_path}: {e}")
            return False
    
    def read_file(self, ftp_path: str) -> bytes:
        """Read a file from FTP server into memory"""
        try:
            remote_full = self._build_remote_path(ftp_path)
            
            # Create temp file
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                # Download file
                success, _ = self._run_rclone(['copy', remote_full, tmp_path], timeout=300)
                if not success:
                    raise Exception("Failed to download file")
                
                # Read file
                with open(tmp_path, 'rb') as f:
                    return f.read()
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        except Exception as e:
            logger.error(f"FTP read_file failed for {ftp_path}: {e}")
            raise
    
    def create_zip_from_path(self, ftp_path: str) -> bytes:
        """Create a zip file containing all files from an FTP path
        
        Args:
            ftp_path: Base path to zip (e.g., /username/gamename)
        
        Returns:
            Bytes of zip file
        """
        try:
            # Download to temp directory
            temp_dir = tempfile.mkdtemp()
            remote_full = self._build_remote_path(ftp_path)
            
            try:
                # Download all files
                success, _ = self._run_rclone(['copy', remote_full, temp_dir, '--recursive'], timeout=600)
                if not success:
                    raise Exception("Failed to download files for zip")
                
                # Create zip from temp directory
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, temp_dir)
                            zipf.write(file_path, arcname)
                
                return zip_buffer.getvalue()
            finally:
                # Clean up temp directory
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
        except Exception as e:
            logger.error(f"FTP create_zip_from_path failed for {ftp_path}: {e}")
            raise


_ftp_storage = None


def get_ftp_storage() -> FTPStorage:
    """Get or create FTP storage instance"""
    global _ftp_storage
    if _ftp_storage is None:
        _ftp_storage = FTPStorage()
    return _ftp_storage

