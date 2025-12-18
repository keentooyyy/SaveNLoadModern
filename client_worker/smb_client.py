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
        # Sanitize inputs first
        server_clean = server.replace('\n', '').replace('\r', '').replace('\t', '').strip()
        share_clean = share.replace('\n', '').replace('\r', '').replace('\t', '').strip()
        username_clean = username.replace('\n', '').replace('\r', '').replace('\t', '').strip()
        
        # Validate share name doesn't contain backslashes or other invalid characters
        if '\\' in share_clean or '/' in share_clean:
            raise ValueError(f"Share name cannot contain path separators: {share_clean}")
        
        self.server = server_clean
        self.share = share_clean
        self.username = username_clean
        self.password = password
        self.domain = domain
        self.port = port
        
        # Register credentials with smbclient
        # Note: domain is not supported by smbclient.register_session
        # If domain is needed, format username as DOMAIN\username
        auth_username = username_clean
        if domain:
            domain_clean = domain.replace('\n', '').replace('\r', '').replace('\t', '').strip()
            auth_username = domain_clean + '\\' + username_clean
        
        smbclient.register_session(
            server_clean,
            username=auth_username,
            password=password,
            port=port
        )
        
        # Build UNC path - use string concatenation to avoid f-string escape issues
        # UNC format: \\server\share
        # Use raw string construction to prevent any escape sequence interpretation
        self.unc_path = '\\\\' + server_clean + '\\' + share_clean
        
        # Verify the path doesn't contain control characters
        if '\n' in self.unc_path or '\r' in self.unc_path:
            raise ValueError(f"UNC path contains control characters: {repr(self.unc_path)}")
        
        # Debug: Print share name to verify it's correct
        print(f"SMB Client initialized: {self.unc_path}")
        print(f"  Share name: {repr(self.share)} (length: {len(self.share)})")
        if '\n' in self.share or '\r' in self.share:
            print(f"  WARNING: Share name contains control characters!")
    
    def _sanitize_path(self, path: str) -> str:
        """Remove control characters and normalize path"""
        if not path:
            return ''
        # Remove newlines, carriage returns, tabs, and other control characters
        sanitized = path.replace('\n', '').replace('\r', '').replace('\t', '').strip()
        return sanitized
    
    def _build_remote_path(self, ftp_path: Optional[str], remote_dir: str = '') -> str:
        """Build remote SMB path from ftp_path, handling UNC paths and share names"""
        if not ftp_path:
            return None
        
        # Sanitize ftp_path
        ftp_path_clean = self._sanitize_path(ftp_path)
        
        # Normalize path separators
        base_path = ftp_path_clean.replace('/', '\\').strip('\\')
        
        # Remove UNC path prefix if present (\\server\share\...)
        if base_path.startswith('\\\\'):
            parts = base_path.split('\\')
            if len(parts) >= 4:
                # Skip server and share (parts[2] and parts[3])
                base_path = '\\'.join(parts[4:])
        
        # Remove any share name if it's already in ftp_path
        # Use case-insensitive comparison and ensure we're matching the full share name
        share_lower = self.share.lower()
        base_path_lower = base_path.lower()
        if base_path_lower.startswith(share_lower + '\\'):
            # Remove share name prefix
            base_path = base_path[len(self.share) + 1:]
        elif base_path_lower == share_lower:
            # If base_path is just the share name, make it empty
            base_path = ''
        
        # Build path parts safely
        path_parts = [p for p in base_path.split('\\') if p and p not in ('.', '..')]
        
        if remote_dir:
            remote_dir_clean = self._sanitize_path(remote_dir)
            remote_dir_normalized = remote_dir_clean.replace('/', '\\').strip('\\')
            dir_parts = [p for p in remote_dir_normalized.split('\\') if p and p not in ('.', '..')]
            path_parts.extend(dir_parts)
        
        if path_parts:
            relative_path = '\\'.join(path_parts)
            return self.unc_path + '\\' + relative_path
        else:
            return self.unc_path
    
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
        
        # Sanitize remote_filename - remove control characters that could corrupt paths
        remote_filename = self._sanitize_path(remote_filename)
        
        try:
            # Build remote path
            remote_dir = os.path.dirname(remote_filename) if os.path.dirname(remote_filename) else ''
            remote_file = os.path.basename(remote_filename)
            
            # Sanitize remote_file as well
            remote_file = self._sanitize_path(remote_file)
            
            # Get full SMB path
            if ftp_path:
                remote_full_path = self._build_remote_path(ftp_path, remote_dir)
            else:
                remote_full_path = self._get_full_path(username, game_name, folder_number, remote_dir)
            
            # Create directory structure if needed
            if remote_dir:
                try:
                    # Extract directory part (everything except the filename)
                    dir_path = remote_full_path
                    smbclient.makedirs(dir_path, exist_ok=True)
                except Exception as e:
                    # Directory might already exist
                    pass
            
            # Build full file path - append filename to directory path
            if remote_file:
                remote_file_path = remote_full_path + '\\' + remote_file
            else:
                remote_file_path = remote_full_path
            
            # Debug: Verify path doesn't contain control characters
            if '\n' in remote_file_path or '\r' in remote_file_path:
                # Show what the UNC path and components are
                debug_info = f"UNC: {repr(self.unc_path)}, remote_full: {repr(remote_full_path)}, file: {repr(remote_file)}"
                return False, f"Path contains invalid characters: {repr(remote_file_path)}. {debug_info}"
            
            # Verify the path starts with the correct UNC prefix
            if not remote_file_path.startswith(self.unc_path):
                return False, f"Path doesn't start with UNC path! Expected: {self.unc_path}, Got: {remote_file_path[:len(self.unc_path)+20]}..."
            
            # Copy file using SMB (very fast - uses native Windows file copy)
            with smbclient.open_file(remote_file_path, mode='wb') as remote_file_handle:
                with open(local_file_path, 'rb') as local_file_handle:
                    # Use shutil.copyfileobj for efficient copying
                    shutil.copyfileobj(local_file_handle, remote_file_handle, length=1024*1024)  # 1MB chunks
            
            return True, "File uploaded successfully"
            
        except Exception as e:
            # Include path info in error for debugging
            error_msg = str(e)
            # Check if path variable exists and add it to error message
            if 'remote_file_path' in locals():
                # Show path representation if it contains control characters
                if '\n' in remote_file_path or '\r' in remote_file_path:
                    path_display = repr(remote_file_path)
                else:
                    path_display = remote_file_path
                return False, f"Upload failed: {error_msg} (Path: {path_display})"
            return False, f"Upload failed: {error_msg}"
    
    def download_save(self, username: str, game_name: str, remote_filename: str,
                     local_file_path: str, folder_number: int, 
                     ftp_path: Optional[str] = None) -> Tuple[bool, str]:
        """Download a save file via SMB - MUCH faster than FTP"""
        try:
            # Sanitize remote_filename
            remote_filename = self._sanitize_path(remote_filename)
            
            # Build remote path
            remote_dir = os.path.dirname(remote_filename) if os.path.dirname(remote_filename) else ''
            remote_file = os.path.basename(remote_filename)
            
            # Sanitize remote_file
            remote_file = self._sanitize_path(remote_file)
            
            # Get full SMB path
            if ftp_path:
                remote_full_path = self._build_remote_path(ftp_path, remote_dir)
            else:
                remote_full_path = self._get_full_path(username, game_name, folder_number, remote_dir)
            
            # Build full file path
            remote_file_path = remote_full_path + '\\' + remote_file
            
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
                remote_path = self._build_remote_path(ftp_path)
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
            # Sanitize remote_dir_path
            remote_dir_path = self._sanitize_path(remote_dir_path)
            
            if ftp_path:
                # Build base path and append directory
                base_path = self._build_remote_path(ftp_path)
                remote_dir_normalized = remote_dir_path.replace('/', '\\').strip('\\')
                if remote_dir_normalized:
                    full_path = base_path + '\\' + remote_dir_normalized
                else:
                    full_path = base_path
            else:
                base_path = self._get_full_path(username, game_name, folder_number)
                remote_dir_normalized = remote_dir_path.replace('/', '\\').strip('\\')
                if remote_dir_normalized:
                    full_path = base_path + '\\' + remote_dir_normalized
                else:
                    full_path = base_path
            
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
        """Delete a directory via SMB (recursively deletes all contents)"""
        try:
            path = ftp_path.replace('/', '\\')
            if not path.startswith('\\'):
                path = f"\\{path}"
            full_path = f"{self.unc_path}{path}"
            
            if not smbclient.path.exists(full_path):
                return True, "Directory already deleted"
            
            # Recursively delete directory contents first
            # smbclient.rmdir doesn't support recursive=True, so we need to do it manually
            def delete_recursive(dir_path):
                """Recursively delete directory contents"""
                try:
                    # List all items in the directory
                    items = smbclient.listdir(dir_path)
                    for item in items:
                        if item in ('.', '..'):
                            continue
                        item_path = f"{dir_path}\\{item}"
                        try:
                            if smbclient.path.isdir(item_path):
                                # Recursively delete subdirectory
                                delete_recursive(item_path)
                                # Delete the now-empty directory
                                smbclient.rmdir(item_path)
                            else:
                                # Delete file
                                smbclient.remove(item_path)
                        except Exception as e:
                            # Continue with other items even if one fails
                            pass
                except Exception as e:
                    # Directory might be empty or already deleted
                    pass
            
            # Delete all contents recursively
            delete_recursive(full_path)
            
            # Delete the directory itself (should be empty now)
            smbclient.rmdir(full_path)
            return True, "Directory deleted"
            
        except Exception as e:
            return False, f"Delete failed: {str(e)}"

