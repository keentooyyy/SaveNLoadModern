"""
Standalone FTP Client Worker
Simplified to only handle file operations - folder tracking is done in Django models
Uses ftputil for robust FTP operations with connection pooling for performance
"""
import os
import ftputil
import threading
import time
from pathlib import Path
from typing import Optional, List, Tuple
from contextlib import contextmanager


class FTPClient:
    """Simplified FTP client - only handles file operations, no folder management
    Uses ftputil for robust FTP operations with connection pooling for performance
    """
    
    def __init__(self, host: str, port: int = 21, username: str = None, 
                 password: str = None, timeout: int = 300):
        """Initialize FTP connection settings
        
        Args:
            timeout: Connection timeout in seconds (default 300 for long operations)
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout  # Increased timeout for long operations
        
        if not self.username or not self.password:
            raise ValueError("FTP username and password must be provided")
        
        # Thread-local storage for connection pooling
        self._local = threading.local()
    
    def _get_connection(self, reuse: bool = False) -> ftputil.FTPHost:
        """Create and return an ftputil FTP connection
        
        Args:
            reuse: If True, try to reuse existing thread-local connection
        
        Returns:
            FTPHost connection
        """
        # Try to reuse existing connection in this thread
        if reuse and hasattr(self._local, 'connection'):
            try:
                # Test if connection is still alive
                self._local.connection.getcwd()
                return self._local.connection
            except Exception:
                # Connection is dead, create new one
                if hasattr(self._local, 'connection'):
                    try:
                        self._local.connection.close()
                    except Exception:
                        pass
                    delattr(self._local, 'connection')
        
        try:
            # Use session factory for custom port with increased timeout
            if self.port != 21:
                session_factory = ftputil.session.session_factory(port=self.port)
                ftp_host = ftputil.FTPHost(self.host, self.username, self.password, 
                                          session_factory=session_factory, timeout=self.timeout)
            else:
                ftp_host = ftputil.FTPHost(self.host, self.username, self.password, timeout=self.timeout)
            
            # Store connection for reuse
            if reuse:
                self._local.connection = ftp_host
            
            return ftp_host
        except Exception as e:
            raise ConnectionError(f"Failed to connect to FTP server: {str(e)}")
    
    @contextmanager
    def batch_operation(self, username: str, game_name: str, folder_number: int, 
                       ftp_path: Optional[str] = None):
        """Context manager for batch operations - reuses connection for multiple files
        
        Usage:
            with ftp_client.batch_operation(username, game_name, folder_number, ftp_path) as (ftp_host, save_folder_path):
                # Perform multiple operations using ftp_host
                ftp_host.upload(file1, remote1)
                ftp_host.upload(file2, remote2)
        """
        ftp_host = None
        try:
            # Get or create connection (reuse if available)
            ftp_host = self._get_connection(reuse=True)
            save_folder_path = self._navigate_to_save_folder(ftp_host, username, game_name, folder_number, ftp_path)
            yield (ftp_host, save_folder_path)
        finally:
            # Don't close connection here - let it be reused
            # Connection will be closed when thread ends or explicitly closed
            pass
    
    def close_connection(self):
        """Close the thread-local connection if it exists"""
        if hasattr(self._local, 'connection'):
            try:
                self._local.connection.close()
            except Exception:
                pass
            delattr(self._local, 'connection')
    
    def _ensure_directory_exists(self, ftp_host: ftputil.FTPHost, path: str) -> None:
        """Ensure a directory path exists on FTP server, creating it if necessary"""
        # Normalize path
        full_path = f"/{path}" if not path.startswith('/') else path
        
        # Check if path exists
        if ftp_host.path.exists(full_path) and ftp_host.path.isdir(full_path):
            return
        
        # Create directory and all parent directories
        try:
            ftp_host.makedirs(full_path)
        except Exception as e:
            raise OSError(f"Failed to create directory: {str(e)}")
    
    def _get_user_game_path(self, username: str, game_name: str) -> str:
        """Get the base path for a user's game on FTP server"""
        safe_game_name = "".join(c for c in game_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_game_name = safe_game_name.replace(' ', '_')
        return f"{username}/{safe_game_name}"
    
    def _navigate_to_save_folder(self, ftp_host: ftputil.FTPHost, username: str, game_name: str, 
                                  folder_number: int, ftp_path: Optional[str] = None) -> str:
        """Navigate to a specific save folder, creating directories if needed
        
        Args:
            ftp_host: FTP connection
            username: Username (used if ftp_path not provided)
            game_name: Game name (used if ftp_path not provided)
            folder_number: Folder number (used if ftp_path not provided)
            ftp_path: Full FTP path (e.g., /username/gamename/save_1). If provided, uses this directly.
        
        Returns:
            Full path to the save folder
        """
        # Use ftp_path directly if provided
        if ftp_path:
            save_folder_path = ftp_path
            # Ensure the path exists
            if not ftp_host.path.exists(save_folder_path) or not ftp_host.path.isdir(save_folder_path):
                try:
                    # Create directory structure
                    ftp_host.makedirs(save_folder_path)
                except Exception as e:
                    # Might already exist, try to navigate
                    if not ftp_host.path.exists(save_folder_path):
                        raise OSError(f"Failed to create save folder: {str(e)}")
            # Navigate to save folder
            ftp_host.chdir(save_folder_path)
            return save_folder_path
        
        # Fallback to constructing path (backward compatibility)
        base_path = self._get_user_game_path(username, game_name)
        save_folder_name = f"save_{folder_number}"
        save_folder_path = f"/{base_path}/{save_folder_name}"
        
        # Ensure base path exists
        base_full_path = f"/{base_path}"
        self._ensure_directory_exists(ftp_host, base_path)
        
        # Navigate to base path
        ftp_host.chdir(base_full_path)
        
        # Check if save folder exists, create if not
        if not ftp_host.path.exists(save_folder_path) or not ftp_host.path.isdir(save_folder_path):
            try:
                ftp_host.mkdir(save_folder_name)
            except Exception as e:
                # Might already exist, try to navigate
                if not ftp_host.path.exists(save_folder_path):
                    raise OSError(f"Failed to create save folder: {str(e)}")
        
        # Navigate to save folder
        ftp_host.chdir(save_folder_path)
        
        return save_folder_path
    
    def create_directory(self, username: str, game_name: str, folder_number: int, 
                        remote_dir_path: str, ftp_path: Optional[str] = None) -> Tuple[bool, str]:
        """Create a directory structure on FTP server (for empty directories)"""
        ftp_host = None
        try:
            ftp_host = self._get_connection()
            save_folder_path = self._navigate_to_save_folder(ftp_host, username, game_name, folder_number, ftp_path)
            
            # Handle nested paths: create directory structure
            if '/' in remote_dir_path or '\\' in remote_dir_path:
                # Normalize to forward slashes
                path_parts = remote_dir_path.replace('\\', '/').split('/')
                # Filter out empty parts
                path_parts = [p for p in path_parts if p]
                
                # Build full path
                full_dir_path = ftp_host.path.join(save_folder_path, *path_parts)
                
                # Create directory structure
                if not ftp_host.path.exists(full_dir_path):
                    try:
                        ftp_host.makedirs(full_dir_path)
                    except Exception as e:
                        return False, f"Failed to create directory structure: {str(e)}"
            else:
                # Single directory name
                full_dir_path = ftp_host.path.join(save_folder_path, remote_dir_path)
                if not ftp_host.path.exists(full_dir_path):
                    try:
                        ftp_host.mkdir(remote_dir_path)
                    except Exception as e:
                        return False, f"Failed to create directory: {str(e)}"
            
            return True, "Directory created"
            
        except Exception as e:
            return False, f"Failed to create directory: {str(e)}"
        finally:
            if ftp_host:
                ftp_host.close()
    
    def upload_save(self, username: str, game_name: str, local_file_path: str, 
                   folder_number: int, remote_filename: Optional[str] = None, 
                   ftp_path: Optional[str] = None, ftp_host: Optional[ftputil.FTPHost] = None,
                   save_folder_path: Optional[str] = None) -> Tuple[bool, str]:
        """Upload a save file to FTP server - 1:1 binary transfer, preserves exact directory structure
        
        Args:
            ftp_host: Optional existing FTP connection to reuse (for batch operations)
            save_folder_path: Optional pre-navigated save folder path (for batch operations)
        """
        if not os.path.exists(local_file_path):
            return False, f"Local file not found: {local_file_path}"
        
        if remote_filename is None:
            remote_filename = os.path.basename(local_file_path)
        
        connection_owner = False
        if ftp_host is None:
            connection_owner = True
            ftp_host = self._get_connection(reuse=True)
        
        try:
            if save_folder_path is None:
                save_folder_path = self._navigate_to_save_folder(ftp_host, username, game_name, folder_number, ftp_path)
            else:
                # Ensure we're in the correct directory
                ftp_host.chdir(save_folder_path)
            
            # Handle nested paths: if remote_filename contains path separators, create directory structure
            if '/' in remote_filename or '\\' in remote_filename:
                # Normalize to forward slashes
                path_parts = remote_filename.replace('\\', '/').split('/')
                # Filter out empty parts
                path_parts = [p for p in path_parts if p]
                
                # Create directory structure (all parts except the filename)
                dir_parts = path_parts[:-1]
                if dir_parts:
                    dir_path = ftp_host.path.join(save_folder_path, *dir_parts)
                    # Check if directory exists, create if not
                    # Handle race condition: multiple workers might try to create same directory
                    if not ftp_host.path.exists(dir_path):
                        try:
                            ftp_host.makedirs(dir_path)
                        except Exception as e:
                            # If directory was created by another thread, that's fine
                            # Check again if it exists now
                            error_str = str(e).lower()
                            if 'exists' in error_str or 'already exists' in error_str:
                                # Directory exists now (created by another worker) - that's OK
                                if not ftp_host.path.exists(dir_path):
                                    # Still doesn't exist, real error
                                    return False, f"Failed to create directory structure: {str(e)}"
                            else:
                                # Different error, check if directory exists now
                                if not ftp_host.path.exists(dir_path):
                                    return False, f"Failed to create directory structure: {str(e)}"
                    # Navigate to directory (might have been created by another worker)
                    try:
                        ftp_host.chdir(dir_path)
                    except Exception as e:
                        # If chdir fails, directory might not exist - try creating again
                        if not ftp_host.path.exists(dir_path):
                            try:
                                ftp_host.makedirs(dir_path)
                                ftp_host.chdir(dir_path)
                            except Exception as e2:
                                return False, f"Failed to navigate to directory: {str(e2)}"
                        else:
                            return False, f"Failed to navigate to directory: {str(e)}"
                
                # Use only the filename (last part)
                remote_filename = path_parts[-1]
            else:
                # Ensure we're in the save folder
                ftp_host.chdir(save_folder_path)
            
            # Build full remote path
            full_remote_path = ftp_host.path.join(ftp_host.getcwd(), remote_filename)
            
            # Check if file exists and delete it first to ensure overwrite
            if ftp_host.path.exists(full_remote_path) and ftp_host.path.isfile(full_remote_path):
                try:
                    ftp_host.remove(full_remote_path)
                except Exception:
                    pass
            
            # Upload file using ftputil with retry logic for connection drops
            max_retries = 3
            retry_count = 0
            last_error = None
            
            while retry_count < max_retries:
                try:
                    ftp_host.upload(local_file_path, remote_filename)
                    return True, "File uploaded successfully"
                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()
                    # Check if it's a connection error that might be recoverable
                    if '10054' in error_str or 'connection' in error_str or 'closed' in error_str:
                        retry_count += 1
                        if retry_count < max_retries:
                            # Close and recreate connection
                            try:
                                if connection_owner and ftp_host:
                                    try:
                                        ftp_host.close()
                                    except:
                                        pass
                                # Get new connection
                                ftp_host = self._get_connection(reuse=False)  # Force new connection
                                # Re-navigate to save folder
                                if save_folder_path:
                                    ftp_host.chdir(save_folder_path)
                                    # Re-navigate to subdirectory if needed
                                    if '/' in remote_filename or '\\' in remote_filename:
                                        path_parts = remote_filename.replace('\\', '/').split('/')
                                        path_parts = [p for p in path_parts if p]
                                        dir_parts = path_parts[:-1]
                                        if dir_parts:
                                            dir_path = ftp_host.path.join(save_folder_path, *dir_parts)
                                            if ftp_host.path.exists(dir_path):
                                                ftp_host.chdir(dir_path)
                                time.sleep(0.5)  # Brief pause before retry
                                continue
                            except Exception as reconnect_error:
                                # If reconnection fails, break and return error
                                last_error = reconnect_error
                                break
                        else:
                            # Max retries reached
                            break
                    else:
                        # Not a retryable error
                        break
            
            return False, f"Upload failed: {str(last_error)}"
            
        except Exception as e:
            return False, f"Upload failed: {str(e)}"
        finally:
            # Only close connection if we created it (not reused)
            if connection_owner:
                # Don't close - let it be reused for next file
                # Connection will be closed when thread ends
                pass
    
    def download_save(self, username: str, game_name: str, remote_filename: str, 
                     local_file_path: str, folder_number: int, ftp_path: Optional[str] = None,
                     ftp_host: Optional[ftputil.FTPHost] = None,
                     save_folder_path: Optional[str] = None) -> Tuple[bool, str]:
        """Download a save file from FTP server - 1:1 binary transfer, no modifications
        
        Args:
            ftp_host: Optional existing FTP connection to reuse (for batch operations)
            save_folder_path: Optional pre-navigated save folder path (for batch operations)
        """
        connection_owner = False
        if ftp_host is None:
            connection_owner = True
            ftp_host = self._get_connection(reuse=True)
        
        try:
            if save_folder_path is None:
                save_folder_path = self._navigate_to_save_folder(ftp_host, username, game_name, folder_number, ftp_path)
            else:
                # Ensure we're in the correct directory
                ftp_host.chdir(save_folder_path)
            
            # Handle nested paths: if remote_filename contains path separators, navigate to directory
            if '/' in remote_filename or '\\' in remote_filename:
                # Normalize to forward slashes
                path_parts = remote_filename.replace('\\', '/').split('/')
                # Filter out empty parts
                path_parts = [p for p in path_parts if p]
                
                # Navigate to directory structure (all parts except the filename)
                dir_parts = path_parts[:-1]
                if dir_parts:
                    dir_path = ftp_host.path.join(save_folder_path, *dir_parts)
                    if not ftp_host.path.exists(dir_path) or not ftp_host.path.isdir(dir_path):
                        return False, f"Directory not found"
                    ftp_host.chdir(dir_path)
                
                # Use only the filename (last part)
                remote_filename = path_parts[-1]
            else:
                # Ensure we're in the save folder
                ftp_host.chdir(save_folder_path)
            
            # Build full remote path
            full_remote_path = ftp_host.path.join(ftp_host.getcwd(), remote_filename)
            
            # Verify file exists
            if not ftp_host.path.exists(full_remote_path) or not ftp_host.path.isfile(full_remote_path):
                return False, f"File not found"
            
            # Download file using ftputil
            ftp_host.download(remote_filename, local_file_path)
            
            return True, "File downloaded successfully"
            
        except Exception as e:
            return False, f"Download failed: {str(e)}"
        finally:
            # Only close connection if we created it (not reused)
            if connection_owner:
                # Don't close - let it be reused for next file
                # Connection will be closed when thread ends
                pass
    
    def _list_recursive(self, ftp_host: ftputil.FTPHost, base_path: str, current_path: str = '') -> Tuple[List[dict], List[str]]:
        """Recursively list all files and directories from FTP"""
        files = []
        directories = []
        
        try:
            # List current directory
            items = ftp_host.listdir(current_path if current_path else '.')
            
            for item in items:
                item_path = ftp_host.path.join(current_path, item) if current_path else item
                full_item_path = ftp_host.path.join(base_path, item_path) if item_path != '.' else base_path
                
                if ftp_host.path.isdir(full_item_path):
                    # It's a directory
                    # Skip . and ..
                    if item in ('.', '..'):
                        continue
                    
                    full_dir_path = item_path
                    directories.append(full_dir_path)
                    
                    # Recursively list subdirectory
                    try:
                        sub_files, sub_dirs = self._list_recursive(ftp_host, base_path, item_path)
                        files.extend(sub_files)
                        directories.extend(sub_dirs)
                    except Exception:
                        pass
                elif ftp_host.path.isfile(full_item_path):
                    # It's a file
                    try:
                        size = ftp_host.path.getsize(full_item_path)
                    except Exception:
                        size = 0
                    
                    files.append({
                        'name': item_path,
                        'size': size
                    })
        except Exception:
            pass
        
        return files, directories
    
    def list_saves(self, username: str, game_name: str, 
                  folder_number: int, ftp_path: Optional[str] = None) -> Tuple[bool, List[dict], List[str], str]:
        """List all save files and directories recursively in a specific save folder"""
        ftp_host = None
        try:
            ftp_host = self._get_connection()
            save_folder_path = self._navigate_to_save_folder(ftp_host, username, game_name, folder_number, ftp_path)
            
            # Recursively list all files and directories
            all_files, all_directories = self._list_recursive(ftp_host, save_folder_path, '.')
            
            return True, all_files, all_directories, f"Found {len(all_files)} file(s) and {len(all_directories)} directory(ies)"
            
        except Exception as e:
            return False, [], [], f"List failed: {str(e)}"
        finally:
            if ftp_host:
                ftp_host.close()
    
    def delete_file(self, ftp_path: str, ftp_host: Optional[ftputil.FTPHost] = None) -> Tuple[bool, str]:
        """Delete a single file from FTP server using full path"""
        connection_owner = False
        if ftp_host is None:
            connection_owner = True
            ftp_host = self._get_connection(reuse=True)
        
        def is_not_found_error(error_str: str) -> bool:
            """Check if error indicates item not found (already deleted)"""
            error_lower = str(error_str).lower()
            not_found_indicators = [
                'not found',
                'no such file',
                'no such directory',
                'directory not found',
                'file not found',
                '550',
                'cwd command failed'
            ]
            return any(indicator in error_lower for indicator in not_found_indicators)
        
        try:
            # Normalize path (ensure it starts with /)
            if not ftp_path.startswith('/'):
                ftp_path = '/' + ftp_path
            
            # Check if already deleted
            try:
                if not ftp_host.path.exists(ftp_path):
                    return True, f"File already deleted: {ftp_path}"
            except Exception as e:
                # If exists() fails with not found error, treat as success
                if is_not_found_error(str(e)):
                    return True, f"File already deleted: {ftp_path}"
                # Otherwise re-raise
                raise
            
            try:
                if not ftp_host.path.isfile(ftp_path):
                    return False, f"Path is not a file: {ftp_path}"
            except Exception as e:
                # If isfile() fails with not found error, treat as success
                if is_not_found_error(str(e)):
                    return True, f"File already deleted: {ftp_path}"
                # Otherwise re-raise
                raise
            
            # Delete file with retries
            max_retries = 3
            for retry in range(max_retries):
                try:
                    ftp_host.remove(ftp_path)
                    return True, f"File deleted: {ftp_path}"
                except Exception as e:
                    error_str = str(e)
                    # If error indicates not found, treat as success
                    if is_not_found_error(error_str):
                        return True, f"File already deleted: {ftp_path}"
                    
                    if retry == max_retries - 1:
                        # Final check - if file doesn't exist, treat as success
                        try:
                            if not ftp_host.path.exists(ftp_path):
                                return True, f"File already deleted: {ftp_path}"
                        except Exception as check_e:
                            # If exists() fails with not found, treat as success
                            if is_not_found_error(str(check_e)):
                                return True, f"File already deleted: {ftp_path}"
                        return False, f"Failed to delete file: {error_str}"
                    time.sleep(0.1)
            
            return False, "Failed to delete file after retries"
        except Exception as e:
            error_str = str(e)
            # If any error indicates not found, treat as success
            if is_not_found_error(error_str):
                return True, f"File already deleted: {ftp_path}"
            return False, f"Delete file failed: {error_str}"
        finally:
            if connection_owner:
                pass  # Don't close - let it be reused
    
    def delete_directory(self, ftp_path: str, ftp_host: Optional[ftputil.FTPHost] = None) -> Tuple[bool, str]:
        """Delete a single directory from FTP server (must be empty) using full path"""
        connection_owner = False
        if ftp_host is None:
            connection_owner = True
            ftp_host = self._get_connection(reuse=True)
        
        def is_not_found_error(error_str: str) -> bool:
            """Check if error indicates item not found (already deleted)"""
            error_lower = str(error_str).lower()
            not_found_indicators = [
                'not found',
                'no such file',
                'no such directory',
                'directory not found',
                'file not found',
                '550',
                'cwd command failed'
            ]
            return any(indicator in error_lower for indicator in not_found_indicators)
        
        try:
            # Normalize path (ensure it starts with /)
            if not ftp_path.startswith('/'):
                ftp_path = '/' + ftp_path
            
            # Check if already deleted
            try:
                if not ftp_host.path.exists(ftp_path):
                    return True, f"Directory already deleted: {ftp_path}"
            except Exception as e:
                # If exists() fails with not found error, treat as success
                if is_not_found_error(str(e)):
                    return True, f"Directory already deleted: {ftp_path}"
                # Otherwise re-raise
                raise
            
            try:
                if not ftp_host.path.isdir(ftp_path):
                    return False, f"Path is not a directory: {ftp_path}"
            except Exception as e:
                # If isdir() fails with not found error, treat as success
                if is_not_found_error(str(e)):
                    return True, f"Directory already deleted: {ftp_path}"
                # Otherwise re-raise
                raise
            
            # Check if directory is empty
            try:
                items = ftp_host.listdir(ftp_path)
                remaining = [x for x in items if x not in ('.', '..')]
                if remaining:
                    # Directory not empty - try to delete remaining items
                    for item in remaining:
                        item_path = ftp_host.path.join(ftp_path, item)
                        try:
                            if ftp_host.path.isdir(item_path):
                                ftp_host.rmdir(item_path)
                            else:
                                ftp_host.remove(item_path)
                        except:
                            pass
            except Exception as e:
                # If listdir fails with not found, directory is already gone - treat as success
                if is_not_found_error(str(e)):
                    return True, f"Directory already deleted: {ftp_path}"
                # Otherwise ignore and continue
                pass
            
            # Delete directory with retries
            max_retries = 5
            for retry in range(max_retries):
                try:
                    # Verify it's empty one more time (if it still exists)
                    try:
                        if ftp_host.path.exists(ftp_path):
                            items = ftp_host.listdir(ftp_path)
                            remaining = [x for x in items if x not in ('.', '..')]
                            if remaining:
                                # Still has items, delete them
                                for item in remaining:
                                    item_path = ftp_host.path.join(ftp_path, item)
                                    try:
                                        if ftp_host.path.isdir(item_path):
                                            ftp_host.rmdir(item_path)
                                        else:
                                            ftp_host.remove(item_path)
                                    except:
                                        pass
                    except Exception as e:
                        # If listdir fails with not found, directory is already gone
                        if is_not_found_error(str(e)):
                            return True, f"Directory already deleted: {ftp_path}"
                        # Otherwise ignore and continue
                        pass
                    
                    # Try to delete the directory
                    ftp_host.rmdir(ftp_path)
                    return True, f"Directory deleted: {ftp_path}"
                except Exception as e:
                    error_str = str(e)
                    # If error indicates not found, treat as success
                    if is_not_found_error(error_str):
                        return True, f"Directory already deleted: {ftp_path}"
                    
                    if retry == max_retries - 1:
                        # Final check - if directory doesn't exist, treat as success
                        try:
                            if not ftp_host.path.exists(ftp_path):
                                return True, f"Directory already deleted: {ftp_path}"
                        except Exception as check_e:
                            # If exists() fails with not found, treat as success
                            if is_not_found_error(str(check_e)):
                                return True, f"Directory already deleted: {ftp_path}"
                        return False, f"Failed to delete directory: {error_str}"
                    time.sleep(0.2 * (retry + 1))
            
            return False, "Failed to delete directory after retries"
        except Exception as e:
            error_str = str(e)
            # If any error indicates not found, treat as success
            if is_not_found_error(error_str):
                return True, f"Directory already deleted: {ftp_path}"
            return False, f"Delete directory failed: {error_str}"
        finally:
            if connection_owner:
                pass  # Don't close - let it be reused
    
    def delete_recursive(self, ftp_path: str, ftp_host: Optional[ftputil.FTPHost] = None, 
                        progress_callback: Optional[callable] = None) -> Tuple[bool, str]:
        """Recursively delete a directory and all its contents - FORCE DELETE (always succeeds)
        
        Args:
            ftp_path: Full FTP path to delete
            ftp_host: Optional existing FTP connection to reuse
            progress_callback: Optional callback function(current, total, item_name) for progress updates
        
        Returns:
            Tuple of (success, message)
        """
        connection_owner = False
        if ftp_host is None:
            connection_owner = True
            ftp_host = self._get_connection(reuse=True)
        
        try:
            # Check if path exists
            if not ftp_host.path.exists(ftp_path):
                return True, f"Path does not exist (already deleted): {ftp_path}"
            
            if not ftp_host.path.isdir(ftp_path):
                # It's a file, just delete it
                if progress_callback:
                    progress_callback(1, 1, os.path.basename(ftp_path))
                try:
                    ftp_host.remove(ftp_path)
                    return True, f"File deleted: {ftp_path}"
                except Exception as e:
                    # Try again - might be a race condition
                    if ftp_host.path.exists(ftp_path):
                        try:
                            ftp_host.remove(ftp_path)
                            return True, f"File deleted: {ftp_path}"
                        except:
                            return False, f"Failed to delete file: {str(e)}"
                    return True, f"File already deleted: {ftp_path}"
            
            # It's a directory - recursively delete all contents
            # First, count all items for progress
            def count_items(path):
                """Count all files and directories recursively"""
                count = 0
                try:
                    items = ftp_host.listdir(path)
                    for item in items:
                        if item in ('.', '..'):
                            continue
                        item_path = ftp_host.path.join(path, item)
                        count += 1
                        if ftp_host.path.isdir(item_path):
                            count += count_items(item_path)
                except:
                    pass
                return count
            
            total_items = count_items(ftp_path) + 1  # +1 for the directory itself
            deleted_count = [0]  # Use list for modification in nested function
            
            def delete_all_contents(path, base_path=None):
                """Delete all files and subdirectories in a path"""
                if base_path is None:
                    base_path = path
                
                deleted_files = 0
                deleted_dirs = 0
                
                try:
                    items = ftp_host.listdir(path)
                    for item in items:
                        # Skip . and ..
                        if item in ('.', '..'):
                            continue
                        
                        item_path = ftp_host.path.join(path, item)
                        rel_path = item_path[len(base_path):].lstrip('/') if item_path.startswith(base_path) else item
                        
                        try:
                            if ftp_host.path.isdir(item_path):
                                # Recursively delete subdirectory
                                sub_files, sub_dirs = delete_all_contents(item_path, base_path)
                                deleted_files += sub_files
                                deleted_dirs += sub_dirs
                                
                                # Delete the directory itself (should be empty now)
                                max_retries = 3
                                for retry in range(max_retries):
                                    try:
                                        # List to verify it's empty
                                        remaining = [x for x in ftp_host.listdir(item_path) if x not in ('.', '..')]
                                        if remaining:
                                            # Still has items, delete them
                                            for remaining_item in remaining:
                                                remaining_path = ftp_host.path.join(item_path, remaining_item)
                                                try:
                                                    if ftp_host.path.isdir(remaining_path):
                                                        delete_all_contents(remaining_path, base_path)
                                                        ftp_host.rmdir(remaining_path)
                                                    else:
                                                        ftp_host.remove(remaining_path)
                                                except:
                                                    pass
                                        ftp_host.rmdir(item_path)
                                        deleted_dirs += 1
                                        deleted_count[0] += 1
                                        if progress_callback:
                                            progress_callback(deleted_count[0], total_items, rel_path)
                                        break
                                    except Exception as e:
                                        if retry == max_retries - 1:
                                            # Last retry failed, but continue
                                            pass
                                        else:
                                            time.sleep(0.1)  # Brief pause before retry
                            else:
                                # It's a file, delete it
                                max_retries = 3
                                for retry in range(max_retries):
                                    try:
                                        ftp_host.remove(item_path)
                                        deleted_files += 1
                                        deleted_count[0] += 1
                                        if progress_callback:
                                            progress_callback(deleted_count[0], total_items, rel_path)
                                        break
                                    except Exception as e:
                                        if retry == max_retries - 1:
                                            # File might already be deleted
                                            if not ftp_host.path.exists(item_path):
                                                deleted_count[0] += 1
                                                if progress_callback:
                                                    progress_callback(deleted_count[0], total_items, rel_path)
                                        else:
                                            time.sleep(0.1)
                        except Exception:
                            # Item might have been deleted by another process, continue
                            pass
                except Exception:
                    # Directory might be empty or already deleted
                    pass
                
                return deleted_files, deleted_dirs
            
            # Delete all contents
            deleted_files, deleted_dirs = delete_all_contents(ftp_path)
            
            # Delete the directory itself - with aggressive retry logic
            max_retries = 10  # More retries for stubborn directories
            for retry in range(max_retries):
                try:
                    # Always verify directory is empty and force delete any remaining items
                    try:
                        remaining = [x for x in ftp_host.listdir(ftp_path) if x not in ('.', '..')]
                    except:
                        remaining = []
                    
                    if remaining:
                        # Still has items, delete them aggressively (multiple passes)
                        for pass_num in range(3):  # Multiple passes to catch everything
                            try:
                                remaining = [x for x in ftp_host.listdir(ftp_path) if x not in ('.', '..')]
                                if not remaining:
                                    break
                                
                                for item in remaining:
                                    item_path = ftp_host.path.join(ftp_path, item)
                                    try:
                                        if ftp_host.path.isdir(item_path):
                                            # Recursively delete again with progress
                                            self.delete_recursive(item_path, ftp_host, progress_callback)
                                        else:
                                            ftp_host.remove(item_path)
                                            deleted_count[0] += 1
                                            if progress_callback:
                                                progress_callback(deleted_count[0], total_items, item)
                                    except Exception as e:
                                        # Item might already be deleted, check if it exists
                                        try:
                                            if ftp_host.path.exists(item_path):
                                                # Still exists, try again
                                                if ftp_host.path.isdir(item_path):
                                                    self.delete_recursive(item_path, ftp_host, progress_callback)
                                                else:
                                                    ftp_host.remove(item_path)
                                        except:
                                            pass
                            except:
                                pass
                            time.sleep(0.1)  # Brief pause between passes
                    
                    # Now try to delete the directory
                    ftp_host.rmdir(ftp_path)
                    deleted_count[0] += 1
                    if progress_callback:
                        progress_callback(deleted_count[0], total_items, os.path.basename(ftp_path))
                    break
                except Exception as e:
                    error_str = str(e).lower()
                    # Check if directory still exists
                    try:
                        if not ftp_host.path.exists(ftp_path):
                            # Directory is gone, success!
                            return True, f"Directory deleted: {ftp_path} (deleted {deleted_files} files, {deleted_dirs} directories)"
                    except:
                        pass
                    
                    if retry == max_retries - 1:
                        # Last retry - one final aggressive attempt
                        try:
                            # List one more time and delete everything
                            final_items = [x for x in ftp_host.listdir(ftp_path) if x not in ('.', '..')]
                            for item in final_items:
                                item_path = ftp_host.path.join(ftp_path, item)
                                try:
                                    if ftp_host.path.isdir(item_path):
                                        self.delete_recursive(item_path, ftp_host, progress_callback)
                                    else:
                                        ftp_host.remove(item_path)
                                except:
                                    pass
                            # Try rmdir one last time
                            ftp_host.rmdir(ftp_path)
                            deleted_count[0] += 1
                            if progress_callback:
                                progress_callback(deleted_count[0], total_items, os.path.basename(ftp_path))
                            return True, f"Directory deleted: {ftp_path} (deleted {deleted_files} files, {deleted_dirs} directories)"
                        except:
                            # Final check - if directory doesn't exist, consider it deleted
                            if not ftp_host.path.exists(ftp_path):
                                return True, f"Directory deleted: {ftp_path} (deleted {deleted_files} files, {deleted_dirs} directories)"
                            return False, f"Failed to delete directory after {max_retries} attempts: {str(e)}"
                    else:
                        time.sleep(0.3 * (retry + 1))  # Increasing delay between retries
            
            return True, f"Successfully deleted directory: {ftp_path} (deleted {deleted_files} files, {deleted_dirs} directories)"
            
        except Exception as e:
            # Final check - if path doesn't exist, consider it deleted
            try:
                if not ftp_host.path.exists(ftp_path):
                    return True, f"Path already deleted: {ftp_path}"
            except:
                pass
            return False, f"Delete failed: {str(e)}"
        finally:
            # Don't close connection if we're reusing it
            if connection_owner:
                pass
