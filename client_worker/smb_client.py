"""
SMB/CIFS Client for SaveNLoad
Much faster than FTP for LAN transfers - can achieve 100+ MB/s on gigabit
"""
import os
import shutil
import threading
from pathlib import Path
from typing import Optional, List, Tuple
try:
    import smbclient
except ImportError:
    smbclient = None

# Alternative: Use smbprotocol (lower-level, faster) or smbclient (higher-level, easier)
# smbclient is easier but smbprotocol is faster

class SMBClient:
    """SMB/CIFS client for fast LAN file transfers
    
    Expected speed: 100-125 MB/s on gigabit LAN (vs 10-30 MB/s with FTP)
    """
    
    def __init__(self, server: str, share: str, username: str, password: str, 
                 domain: str = None, port: int = 445):
        """Initialize SMB connection
        
        Args:
            server: SMB server hostname/IP
            share: Share name (e.g., 'saves' or 'SaveNLoad')
            username: SMB username
            password: SMB password
            domain: Domain name (optional, usually None for workgroup)
            port: SMB port (default 445)
        """
        self.server = server
        self.share = share
        self.username = username
        self.password = password
        self.domain = domain
        self.port = port
        
        # Register credentials with smbclient
        smbclient.register_session(
            server,
            username=username,
            password=password,
            domain=domain,
            port=port
        )
        
        # Build UNC path
        self.unc_path = f"\\\\{server}\\{share}"
        
        print(f"SMB Client initialized: {self.unc_path}")
    
    def _get_full_path(self, username: str, game_name: str, folder_number: int, 
                      remote_path: str = '') -> str:
        """Build full SMB path for save folder"""
        safe_game_name = "".join(c for c in game_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_game_name = safe_game_name.replace(' ', '_')
        
        base_path = f"{username}\\{safe_game_name}\\save_{folder_number}"
        if remote_path:
            # Normalize path separators
            remote_path = remote_path.replace('/', '\\')
            if remote_path.startswith('\\'):
                remote_path = remote_path[1:]
            full_path = f"{base_path}\\{remote_path}"
        else:
            full_path = base_path
        
        return f"{self.unc_path}\\{full_path}"
    
    def upload_save(self, username: str, game_name: str, local_file_path: str,
                   folder_number: int, remote_filename: Optional[str] = None,
                   ftp_path: Optional[str] = None) -> Tuple[bool, str]:
        """Upload a save file via SMB - MUCH faster than FTP"""
        if not os.path.exists(local_file_path):
            return False, f"Local file not found: {local_file_path}"
        
        if remote_filename is None:
            remote_filename = os.path.basename(local_file_path)
        
        try:
            # Build remote path
            remote_dir = os.path.dirname(remote_filename) if os.path.dirname(remote_filename) else ''
            remote_file = os.path.basename(remote_filename)
            
            # Get full SMB path
            if ftp_path:
                # Use ftp_path directly (convert to SMB path format)
                base_path = ftp_path.replace('/', '\\')
                if base_path.startswith('\\'):
                    base_path = base_path[1:]
                remote_full_path = f"{self.unc_path}\\{base_path}"
                if remote_dir:
                    remote_full_path = f"{remote_full_path}\\{remote_dir}"
            else:
                remote_full_path = self._get_full_path(username, game_name, folder_number, remote_dir)
            
            # Create directory structure if needed
            if remote_dir:
                try:
                    smbclient.makedirs(remote_full_path, exist_ok=True)
                except Exception as e:
                    # Directory might already exist
                    pass
            
            # Build full file path
            remote_file_path = f"{remote_full_path}\\{remote_file}"
            
            # Copy file using SMB (very fast - uses native Windows file copy)
            with smbclient.open_file(remote_file_path, mode='wb') as remote_file_handle:
                with open(local_file_path, 'rb') as local_file_handle:
                    # Use shutil.copyfileobj for efficient copying
                    shutil.copyfileobj(local_file_handle, remote_file_handle, length=1024*1024)  # 1MB chunks
            
            return True, "File uploaded successfully"
            
        except Exception as e:
            return False, f"Upload failed: {str(e)}"
    
    def download_save(self, username: str, game_name: str, remote_filename: str,
                     local_file_path: str, folder_number: int, 
                     ftp_path: Optional[str] = None) -> Tuple[bool, str]:
        """Download a save file via SMB - MUCH faster than FTP"""
        try:
            # Build remote path
            remote_dir = os.path.dirname(remote_filename) if os.path.dirname(remote_filename) else ''
            remote_file = os.path.basename(remote_filename)
            
            # Get full SMB path
            if ftp_path:
                base_path = ftp_path.replace('/', '\\')
                if base_path.startswith('\\'):
                    base_path = base_path[1:]
                remote_full_path = f"{self.unc_path}\\{base_path}"
                if remote_dir:
                    remote_full_path = f"{remote_full_path}\\{remote_dir}"
            else:
                remote_full_path = self._get_full_path(username, game_name, folder_number, remote_dir)
            
            # Build full file path
            remote_file_path = f"{remote_full_path}\\{remote_file}"
            
            # Verify file exists
            if not smbclient.path.exists(remote_file_path):
                return False, "File not found"
            
            # Create local directory if needed
            local_dir = os.path.dirname(local_file_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)
            
            # Copy file using SMB (very fast)
            with smbclient.open_file(remote_file_path, mode='rb') as remote_file_handle:
                with open(local_file_path, 'wb') as local_file_handle:
                    shutil.copyfileobj(remote_file_handle, local_file_handle, length=1024*1024)  # 1MB chunks
            
            return True, "File downloaded successfully"
            
        except Exception as e:
            return False, f"Download failed: {str(e)}"
    
    def list_saves(self, username: str, game_name: str, folder_number: int,
                  ftp_path: Optional[str] = None) -> Tuple[bool, List[dict], List[str], str]:
        """List all save files recursively via SMB"""
        try:
            # Get base path
            if ftp_path:
                base_path = ftp_path.replace('/', '\\')
                if base_path.startswith('\\'):
                    base_path = base_path[1:]
                remote_path = f"{self.unc_path}\\{base_path}"
            else:
                remote_path = self._get_full_path(username, game_name, folder_number)
            
            if not smbclient.path.exists(remote_path):
                return False, [], [], "Path not found"
            
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
                except Exception:
                    pass
            
            walk_directory(remote_path, remote_path)
            
            return True, files, directories, f"Found {len(files)} file(s) and {len(directories)} directory(ies)"
            
        except Exception as e:
            return False, [], [], f"List failed: {str(e)}"
    
    def create_directory(self, username: str, game_name: str, folder_number: int,
                        remote_dir_path: str, ftp_path: Optional[str] = None) -> Tuple[bool, str]:
        """Create directory structure via SMB"""
        try:
            if ftp_path:
                base_path = ftp_path.replace('/', '\\')
                if base_path.startswith('\\'):
                    base_path = base_path[1:]
                full_path = f"{self.unc_path}\\{base_path}\\{remote_dir_path.replace('/', '\\')}"
            else:
                base_path = self._get_full_path(username, game_name, folder_number)
                full_path = f"{base_path}\\{remote_dir_path.replace('/', '\\')}"
            
            smbclient.makedirs(full_path, exist_ok=True)
            return True, "Directory created"
            
        except Exception as e:
            return False, f"Failed to create directory: {str(e)}"
    
    def delete_file(self, ftp_path: str) -> Tuple[bool, str]:
        """Delete a file via SMB"""
        try:
            path = ftp_path.replace('/', '\\')
            if not path.startswith('\\'):
                path = f"\\{path}"
            full_path = f"{self.unc_path}{path}"
            
            if not smbclient.path.exists(full_path):
                return True, "File already deleted"
            
            smbclient.remove(full_path)
            return True, "File deleted"
            
        except Exception as e:
            return False, f"Delete failed: {str(e)}"
    
    def delete_directory(self, ftp_path: str) -> Tuple[bool, str]:
        """Delete a directory via SMB"""
        try:
            path = ftp_path.replace('/', '\\')
            if not path.startswith('\\'):
                path = f"\\{path}"
            full_path = f"{self.unc_path}{path}"
            
            if not smbclient.path.exists(full_path):
                return True, "Directory already deleted"
            
            # Recursively delete directory
            smbclient.rmdir(full_path, recursive=True)
            return True, "Directory deleted"
            
        except Exception as e:
            return False, f"Delete failed: {str(e)}"

