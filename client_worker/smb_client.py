"""
SMB/CIFS Client for SaveNLoad
SMB/CIFS client for fast LAN transfers - can achieve 100+ MB/s on gigabit
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
    
    Expected speed: 100-125 MB/s on gigabit LAN
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
    
    def _build_remote_path(self, smb_path: Optional[str], remote_dir: str = '') -> str:
        """Build remote SMB path from smb_path, handling UNC paths and share names"""
        if not smb_path:
            return None
        
        # Sanitize smb_path
        smb_path_clean = self._sanitize_path(smb_path)
        
        # Normalize path separators
        base_path = smb_path_clean.replace('/', '\\').strip('\\')
        
        # Remove UNC path prefix if present (\\server\share\...)
        if base_path.startswith('\\\\'):
            parts = base_path.split('\\')
            if len(parts) >= 4:
                # Skip server and share (parts[2] and parts[3])
                base_path = '\\'.join(parts[4:])
        
        # Remove any share name if it's already in smb_path
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
                   smb_path: Optional[str] = None) -> Tuple[bool, str]:
        """Upload a save file via SMB"""
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
            if smb_path:
                remote_full_path = self._build_remote_path(smb_path, remote_dir)
            else:
                remote_full_path = self._get_full_path(username, game_name, folder_number, remote_dir)
            
            # Build full file path - append filename to directory path
            if remote_file:
                remote_file_path = remote_full_path + '\\' + remote_file
            else:
                remote_file_path = remote_full_path
            
            # Always create the full directory structure if needed (including base save folder)
            # Extract directory part - this is the directory that will contain the file
            # For files: directory is parent of file path
            # For directories: directory is the path itself
            if remote_file:
                # We have a filename, so get the parent directory
                remote_dir_path = os.path.dirname(remote_file_path)
            else:
                # No filename, so the path itself is the directory
                remote_dir_path = remote_file_path
            
            # Always create the directory structure (makedirs creates all parent dirs too)
            if remote_dir_path:
                try:
                    smbclient.makedirs(remote_dir_path, exist_ok=True)
                except Exception as dir_error:
                    # If directory creation fails, return error instead of continuing
                    return False, f"Failed to create SMB directory: {remote_dir_path} - {str(dir_error)}"
            
            # Debug: Verify path doesn't contain control characters
            if '\n' in remote_file_path or '\r' in remote_file_path:
                # Show what the UNC path and components are
                debug_info = f"UNC: {repr(self.unc_path)}, remote_full: {repr(remote_full_path)}, file: {repr(remote_file)}"
                return False, f"Path contains invalid characters: {repr(remote_file_path)}. {debug_info}"
            
            # Verify the path starts with the correct UNC prefix
            if not remote_file_path.startswith(self.unc_path):
                return False, f"Path doesn't start with UNC path! Expected: {self.unc_path}, Got: {remote_file_path[:len(self.unc_path)+20]}..."
            
            # Copy file using SMB (very fast - uses native Windows file copy)
            # Retry on credit exhaustion and file locking errors
            import time
            import gc
            max_retries = 5
            base_retry_delay = 0.5  # 500ms base delay
            for attempt in range(max_retries):
                remote_file_handle = None
                local_file_handle = None
                try:
                    # Open files with explicit context managers to ensure cleanup
                    remote_file_handle = smbclient.open_file(remote_file_path, mode='wb')
                    try:
                        local_file_handle = open(local_file_path, 'rb')
                        try:
                            # Use shutil.copyfileobj for efficient copying
                            shutil.copyfileobj(local_file_handle, remote_file_handle, length=1024*1024)  # 1MB chunks
                        finally:
                            # Explicitly close local file handle
                            if local_file_handle:
                                local_file_handle.close()
                                local_file_handle = None
                    finally:
                        # Explicitly close remote file handle
                        if remote_file_handle:
                            remote_file_handle.close()
                            remote_file_handle = None
                    
                    # Force garbage collection to ensure file handles are released
                    gc.collect()
                    return True, "File uploaded successfully"
                    
                except Exception as retry_error:
                    # Ensure handles are closed even on error
                    try:
                        if local_file_handle:
                            local_file_handle.close()
                    except:
                        pass
                    try:
                        if remote_file_handle:
                            remote_file_handle.close()
                    except:
                        pass
                    
                    # Force cleanup
                    gc.collect()
                    
                    error_str = str(retry_error)
                    # Check if it's a retryable error
                    is_retryable = False
                    retry_delay = base_retry_delay
                    
                    if 'credits' in error_str.lower():
                        # Credit exhaustion - need longer delay to allow connection pool to recover
                        is_retryable = True
                        retry_delay = 1.0 + (attempt * 0.5)  # 1s, 1.5s, 2s, 2.5s, 3s
                    elif 'being used by another process' in error_str or 'c0000043' in error_str:
                        # File locked - need longer delay to allow file to be released
                        is_retryable = True
                        retry_delay = 0.5 + (attempt * 0.3)  # 0.5s, 0.8s, 1.1s, 1.4s, 1.7s
                    elif 'access denied' in error_str.lower() and 'c0000022' in error_str:
                        # Sometimes access denied is temporary
                        is_retryable = True
                        retry_delay = base_retry_delay * (attempt + 1)
                    
                    if is_retryable and attempt < max_retries - 1:
                        # Wait with calculated delay to allow connections/files to be released
                        time.sleep(retry_delay)
                        continue
                    else:
                        # Not a retryable error or out of retries, re-raise
                        raise retry_error
            
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
                     smb_path: Optional[str] = None) -> Tuple[bool, str]:
        """Download a save file via SMB"""
        try:
            # Sanitize remote_filename
            remote_filename = self._sanitize_path(remote_filename)
            
            # Build remote path
            remote_dir = os.path.dirname(remote_filename) if os.path.dirname(remote_filename) else ''
            remote_file = os.path.basename(remote_filename)
            
            # Sanitize remote_file
            remote_file = self._sanitize_path(remote_file)
            
            # Get full SMB path
            if smb_path:
                remote_full_path = self._build_remote_path(smb_path, remote_dir)
            else:
                remote_full_path = self._get_full_path(username, game_name, folder_number, remote_dir)
            
            # Build full file path
            remote_file_path = remote_full_path + '\\' + remote_file
            
            # Verify file exists
            if not smbclient.path.exists(remote_file_path):
                return False, "File not found"
            
            # Always create local directory structure if needed (including all parent directories)
            local_dir = os.path.dirname(local_file_path)
            if local_dir:  # Only create if there's a directory path (not root/current dir)
                try:
                    os.makedirs(local_dir, exist_ok=True)
                except OSError as dir_error:
                    return False, f"Failed to create directory: {local_dir} - {str(dir_error)}"
            
            # Copy file using SMB (very fast)
            # Retry on credit exhaustion and file locking errors
            import time
            import gc
            max_retries = 5
            base_retry_delay = 0.5  # 500ms base delay
            for attempt in range(max_retries):
                remote_file_handle = None
                local_file_handle = None
                try:
                    # Open files with explicit context managers to ensure cleanup
                    remote_file_handle = smbclient.open_file(remote_file_path, mode='rb')
                    try:
                        local_file_handle = open(local_file_path, 'wb')
                        try:
                            shutil.copyfileobj(remote_file_handle, local_file_handle, length=1024*1024)  # 1MB chunks
                        finally:
                            # Explicitly close local file handle
                            if local_file_handle:
                                local_file_handle.close()
                                local_file_handle = None
                    finally:
                        # Explicitly close remote file handle
                        if remote_file_handle:
                            remote_file_handle.close()
                            remote_file_handle = None
                    
                    # Force garbage collection to ensure file handles are released
                    gc.collect()
                    return True, "File downloaded successfully"
                    
                except Exception as retry_error:
                    # Ensure handles are closed even on error
                    try:
                        if local_file_handle:
                            local_file_handle.close()
                    except:
                        pass
                    try:
                        if remote_file_handle:
                            remote_file_handle.close()
                    except:
                        pass
                    
                    # Force cleanup
                    gc.collect()
                    
                    error_str = str(retry_error)
                    # Check if it's a retryable error
                    is_retryable = False
                    retry_delay = base_retry_delay
                    
                    if 'credits' in error_str.lower():
                        # Credit exhaustion - need longer delay to allow connection pool to recover
                        is_retryable = True
                        retry_delay = 1.0 + (attempt * 0.5)  # 1s, 1.5s, 2s, 2.5s, 3s
                    elif 'being used by another process' in error_str or 'c0000043' in error_str:
                        # File locked - need longer delay to allow file to be released
                        is_retryable = True
                        retry_delay = 0.5 + (attempt * 0.3)  # 0.5s, 0.8s, 1.1s, 1.4s, 1.7s
                    elif 'access denied' in error_str.lower() and 'c0000022' in error_str:
                        # Sometimes access denied is temporary
                        is_retryable = True
                        retry_delay = base_retry_delay * (attempt + 1)
                    
                    if is_retryable and attempt < max_retries - 1:
                        # Wait with calculated delay to allow connections/files to be released
                        time.sleep(retry_delay)
                        continue
                    else:
                        # Not a retryable error or out of retries, re-raise
                        raise retry_error
            
            return True, "File downloaded successfully"
            
        except Exception as e:
            return False, f"Download failed: {str(e)}"
    
    def list_saves(self, username: str, game_name: str, folder_number: int,
                  smb_path: Optional[str] = None) -> Tuple[bool, List[dict], List[str], str]:
        """List all save files recursively via SMB"""
        try:
            # Get base path
            if smb_path:
                remote_path = self._build_remote_path(smb_path)
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
                        remote_dir_path: str, smb_path: Optional[str] = None) -> Tuple[bool, str]:
        """Create directory structure via SMB"""
        try:
            # Sanitize remote_dir_path
            remote_dir_path = self._sanitize_path(remote_dir_path)
            
            if smb_path:
                # Build base path and append directory
                base_path = self._build_remote_path(smb_path)
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
    
    def delete_file(self, smb_path: str) -> Tuple[bool, str]:
        """Delete a file via SMB"""
        import time
        import gc
        max_retries = 5
        base_retry_delay = 0.5  # 500ms base delay
        
        try:
            path = smb_path.replace('/', '\\')
            if not path.startswith('\\'):
                path = f"\\{path}"
            full_path = f"{self.unc_path}{path}"
            
            if not smbclient.path.exists(full_path):
                return True, "File already deleted"
            
            for attempt in range(max_retries):
                try:
                    smbclient.remove(full_path)
                    # Force cleanup after successful operation
                    gc.collect()
                    return True, "File deleted"
                except Exception as retry_error:
                    # Force cleanup on error
                    gc.collect()
                    
                    error_str = str(retry_error)
                    # Check if it's a retryable error
                    is_retryable = False
                    retry_delay = base_retry_delay
                    
                    if 'credits' in error_str.lower():
                        # Credit exhaustion - need longer delay to allow connection pool to recover
                        is_retryable = True
                        retry_delay = 1.0 + (attempt * 0.5)  # 1s, 1.5s, 2s, 2.5s, 3s
                    elif 'being used by another process' in error_str or 'c0000043' in error_str:
                        # File locked - need longer delay to allow file to be released
                        is_retryable = True
                        retry_delay = 0.5 + (attempt * 0.3)  # 0.5s, 0.8s, 1.1s, 1.4s, 1.7s
                    elif 'access denied' in error_str.lower() and 'c0000022' in error_str:
                        # Sometimes access denied is temporary
                        is_retryable = True
                        retry_delay = base_retry_delay * (attempt + 1)
                    
                    if is_retryable and attempt < max_retries - 1:
                        # Wait with calculated delay to allow connections/files to be released
                        time.sleep(retry_delay)
                        continue
                    else:
                        # Not a retryable error or out of retries, return error
                        return False, f"Delete failed: {str(retry_error)}"
            
        except Exception as e:
            return False, f"Delete failed: {str(e)}"
    
    def delete_directory(self, smb_path: str) -> Tuple[bool, str]:
        """Delete a directory via SMB (recursively deletes all contents)"""
        import time
        import gc
        
        try:
            path = smb_path.replace('/', '\\')
            if not path.startswith('\\'):
                path = f"\\{path}"
            full_path = f"{self.unc_path}{path}"
            
            if not smbclient.path.exists(full_path):
                return True, "Directory already deleted"
            
            # Recursively delete directory contents first
            # smbclient.rmdir doesn't support recursive=True, so we need to do it manually
            def delete_recursive(dir_path, max_retries=3):
                """Recursively delete directory contents with retry logic"""
                try:
                    # List all items in the directory
                    items = smbclient.listdir(dir_path)
                    for item in items:
                        if item in ('.', '..'):
                            continue
                        item_path = f"{dir_path}\\{item}"
                        
                        # Retry logic for each item
                        for attempt in range(max_retries):
                            try:
                                if smbclient.path.isdir(item_path):
                                    # Recursively delete subdirectory
                                    delete_recursive(item_path, max_retries)
                                    # Delete the now-empty directory
                                    smbclient.rmdir(item_path)
                                else:
                                    # Delete file
                                    smbclient.remove(item_path)
                                break  # Success, exit retry loop
                            except Exception as item_error:
                                error_str = str(item_error)
                                # Check if it's a retryable error
                                is_retryable = ('credits' in error_str.lower() or 
                                               'being used by another process' in error_str or 
                                               'c0000043' in error_str or
                                               ('access denied' in error_str.lower() and 'c0000022' in error_str))
                                
                                if is_retryable and attempt < max_retries - 1:
                                    time.sleep(0.3 + (attempt * 0.2))
                                    gc.collect()
                                    continue
                                else:
                                    # Not retryable or out of retries, continue with next item
                                    break
                except Exception as e:
                    # Directory might be empty or already deleted
                    pass
            
            # Delete all contents recursively
            delete_recursive(full_path)
            
            # Delete the directory itself (should be empty now) with retry logic
            max_retries = 5
            base_retry_delay = 0.5
            for attempt in range(max_retries):
                try:
                    smbclient.rmdir(full_path)
                    # Force cleanup after successful operation
                    gc.collect()
                    return True, "Directory deleted"
                except Exception as retry_error:
                    # Force cleanup on error
                    gc.collect()
                    
                    error_str = str(retry_error)
                    # Check if it's a retryable error
                    is_retryable = False
                    retry_delay = base_retry_delay
                    
                    if 'credits' in error_str.lower():
                        # Credit exhaustion - need longer delay to allow connection pool to recover
                        is_retryable = True
                        retry_delay = 1.0 + (attempt * 0.5)  # 1s, 1.5s, 2s, 2.5s, 3s
                    elif 'being used by another process' in error_str or 'c0000043' in error_str:
                        # File locked - need longer delay to allow file to be released
                        is_retryable = True
                        retry_delay = 0.5 + (attempt * 0.3)  # 0.5s, 0.8s, 1.1s, 1.4s, 1.7s
                    elif 'access denied' in error_str.lower() and 'c0000022' in error_str:
                        # Sometimes access denied is temporary
                        is_retryable = True
                        retry_delay = base_retry_delay * (attempt + 1)
                    
                    if is_retryable and attempt < max_retries - 1:
                        # Wait with calculated delay to allow connections/files to be released
                        time.sleep(retry_delay)
                        continue
                    else:
                        # Not a retryable error or out of retries, return error
                        return False, f"Delete failed: {str(retry_error)}"
            
        except Exception as e:
            return False, f"Delete failed: {str(e)}"

