"""
SMB/CIFS Storage Utility for Django Backend
Replaces FTP for much faster file operations on LAN
"""
import os
import io
import zipfile
import logging
from typing import List, Tuple, Optional
import smbclient

logger = logging.getLogger(__name__)


class SMBStorage:
    """SMB/CIFS storage backend for save files
    
    Much faster than FTP - can achieve 100+ MB/s on gigabit LAN
    """
    
    def __init__(self):
        """Initialize SMB storage with credentials from environment"""
        self.server = os.getenv('SMB_SERVER')
        self.share = os.getenv('SMB_SHARE', 'SaveNLoad')
        self.username = os.getenv('SMB_USERNAME')
        self.password = os.getenv('SMB_PASSWORD')
        self.domain = os.getenv('SMB_DOMAIN')  # Optional, usually None for workgroup
        self.port = int(os.getenv('SMB_PORT', '445'))
        
        if not all([self.server, self.username, self.password]):
            raise ValueError("SMB credentials must be set in environment variables (SMB_SERVER, SMB_SHARE, SMB_USERNAME, SMB_PASSWORD)")
        
        # Register SMB session
        smbclient.register_session(
            self.server,
            username=self.username,
            password=self.password,
            domain=self.domain,
            port=self.port
        )
        
        # Build UNC path
        self.unc_path = f"\\\\{self.server}\\{self.share}"
        
        logger.info(f"SMB Storage initialized: {self.unc_path}")
    
    def _get_full_path(self, smb_path: str) -> str:
        """Convert SMB path to full UNC path
        
        Args:
            smb_path: Path relative to share (e.g., /username/gamename/save_1)
        
        Returns:
            Full UNC path (e.g., \\\\server\\share\\username\\gamename\\save_1)
        """
        # Normalize path - remove leading slash, convert to Windows separators
        normalized = smb_path.lstrip('/').replace('/', '\\')
        return f"{self.unc_path}\\{normalized}"
    
    def path_exists(self, smb_path: str) -> bool:
        """Check if path exists on SMB share"""
        try:
            full_path = self._get_full_path(smb_path)
            return smbclient.path.exists(full_path)
        except Exception as e:
            logger.error(f"SMB path_exists failed for {smb_path}: {e}")
            return False
    
    def is_directory(self, smb_path: str) -> bool:
        """Check if path is a directory"""
        try:
            full_path = self._get_full_path(smb_path)
            return smbclient.path.isdir(full_path)
        except Exception:
            return False
    
    def list_directory(self, smb_path: str) -> Tuple[List[str], List[str]]:
        """List files and directories in a path
        
        Returns:
            Tuple of (files, directories)
        """
        try:
            full_path = self._get_full_path(smb_path)
            if not smbclient.path.exists(full_path):
                return [], []
            
            files = []
            directories = []
            
            for item in smbclient.listdir(full_path):
                if item in ('.', '..'):
                    continue
                
                item_path = f"{full_path}\\{item}"
                if smbclient.path.isdir(item_path):
                    directories.append(item)
                else:
                    files.append(item)
            
            return files, directories
        except Exception as e:
            logger.error(f"SMB list_directory failed for {smb_path}: {e}")
            return [], []
    
    def list_recursive(self, smb_path: str) -> Tuple[List[dict], List[str]]:
        """Recursively list all files and directories
        
        Returns:
            Tuple of (files_list, directories_list)
            files_list: List of dicts with 'name' and 'size'
            directories_list: List of directory paths (relative)
        """
        files = []
        directories = []
        
        def walk_directory(path, base_path):
            """Recursively walk directory"""
            try:
                for item in smbclient.listdir(path):
                    if item in ('.', '..'):
                        continue
                    
                    item_path = f"{path}\\{item}"
                    rel_path = item_path[len(base_path):].lstrip('\\')
                    
                    if smbclient.path.isdir(item_path):
                        directories.append(rel_path.replace('\\', '/'))
                        walk_directory(item_path, base_path)
                    else:
                        try:
                            size = smbclient.path.getsize(item_path)
                        except:
                            size = 0
                        files.append({
                            'name': rel_path.replace('\\', '/'),
                            'size': size
                        })
            except Exception as e:
                logger.debug(f"Error walking directory {path}: {e}")
        
        try:
            full_path = self._get_full_path(smb_path)
            if not smbclient.path.exists(full_path):
                return [], []
            
            walk_directory(full_path, full_path)
            return files, directories
        except Exception as e:
            logger.error(f"SMB list_recursive failed for {smb_path}: {e}")
            return [], []
    
    def create_directory(self, smb_path: str) -> bool:
        """Create directory structure (creates parent directories if needed)"""
        try:
            full_path = self._get_full_path(smb_path)
            smbclient.makedirs(full_path, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"SMB create_directory failed for {smb_path}: {e}")
            return False
    
    def delete_file(self, smb_path: str) -> bool:
        """Delete a file"""
        try:
            full_path = self._get_full_path(smb_path)
            if smbclient.path.exists(full_path):
                smbclient.remove(full_path)
            return True
        except Exception as e:
            logger.error(f"SMB delete_file failed for {smb_path}: {e}")
            return False
    
    def delete_directory(self, smb_path: str, recursive: bool = True) -> bool:
        """Delete a directory
        
        Args:
            smb_path: Path to directory
            recursive: If True, delete all contents recursively
        """
        try:
            full_path = self._get_full_path(smb_path)
            if smbclient.path.exists(full_path):
                if recursive:
                    smbclient.rmdir(full_path, recursive=True)
                else:
                    smbclient.rmdir(full_path)
            return True
        except Exception as e:
            logger.error(f"SMB delete_directory failed for {smb_path}: {e}")
            return False
    
    def read_file(self, smb_path: str) -> bytes:
        """Read a file from SMB share into memory"""
        try:
            full_path = self._get_full_path(smb_path)
            with smbclient.open_file(full_path, mode='rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"SMB read_file failed for {smb_path}: {e}")
            raise
    
    def create_zip_from_path(self, smb_path: str) -> bytes:
        """Create a zip file containing all files from an SMB path
        
        Args:
            smb_path: Base path to zip (e.g., /username/gamename)
        
        Returns:
            Zip file as bytes
        """
        zip_buffer = io.BytesIO()
        
        try:
            full_path = self._get_full_path(smb_path)
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                def add_to_zip(current_path, base_path, zip_prefix=''):
                    """Recursively add files to zip"""
                    try:
                        for item in smbclient.listdir(current_path):
                            if item in ('.', '..'):
                                continue
                            
                            item_path = f"{current_path}\\{item}"
                            rel_path = item_path[len(base_path):].lstrip('\\')
                            zip_name = f"{zip_prefix}{rel_path}".replace('\\', '/')
                            
                            if smbclient.path.isdir(item_path):
                                # Add directory entry (some zip tools need this)
                                zip_file.writestr(f"{zip_name}/", b'')
                                add_to_zip(item_path, base_path, zip_prefix)
                            else:
                                # Read file and add to zip
                                with smbclient.open_file(item_path, 'rb') as f:
                                    zip_file.writestr(zip_name, f.read())
                    except Exception as e:
                        logger.debug(f"Error adding {current_path} to zip: {e}")
                
                if smbclient.path.exists(full_path):
                    add_to_zip(full_path, full_path)
            
            zip_buffer.seek(0)
            return zip_buffer.read()
            
        except Exception as e:
            logger.error(f"SMB create_zip_from_path failed for {smb_path}: {e}")
            raise


# Global instance (initialized on first use)
_smb_storage = None


def get_smb_storage() -> SMBStorage:
    """Get or create SMB storage instance"""
    global _smb_storage
    if _smb_storage is None:
        _smb_storage = SMBStorage()
    return _smb_storage

