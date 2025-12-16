"""
Standalone FTP Client Worker
Simplified to only handle file operations - folder tracking is done in Django models
Uses ftputil for robust FTP operations
"""
import os
import ftputil
from pathlib import Path
from typing import Optional, List, Tuple


class FTPClient:
    """Simplified FTP client - only handles file operations, no folder management
    Uses ftputil for robust FTP operations
    """
    
    def __init__(self, host: str, port: int = 21, username: str = None, 
                 password: str = None, timeout: int = 30):
        """Initialize FTP connection settings"""
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        
        if not self.username or not self.password:
            raise ValueError("FTP username and password must be provided")
    
    def _get_connection(self) -> ftputil.FTPHost:
        """Create and return an ftputil FTP connection"""
        try:
            # Use session factory for custom port
            if self.port != 21:
                session_factory = ftputil.session.session_factory(port=self.port)
                ftp_host = ftputil.FTPHost(self.host, self.username, self.password, session_factory=session_factory)
            else:
                ftp_host = ftputil.FTPHost(self.host, self.username, self.password)
            return ftp_host
        except Exception as e:
            print(f"ERROR: Failed to connect to FTP server: {e}")
            raise
    
    def _ensure_directory_exists(self, ftp_host: ftputil.FTPHost, path: str) -> None:
        """Ensure a directory path exists on FTP server, creating it if necessary"""
        # Normalize path
        full_path = f"/{path}" if not path.startswith('/') else path
        
        # Check if path exists
        if ftp_host.path.exists(full_path) and ftp_host.path.isdir(full_path):
            print(f"DEBUG: Directory exists: {full_path}")
            return
        
        # Create directory and all parent directories
        try:
            ftp_host.makedirs(full_path)
            print(f"INFO: Created FTP directory: {full_path}")
        except Exception as e:
            print(f"ERROR: Failed to create directory {full_path}: {e}")
            raise
    
    def _get_user_game_path(self, username: str, game_name: str) -> str:
        """Get the base path for a user's game on FTP server"""
        safe_game_name = "".join(c for c in game_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_game_name = safe_game_name.replace(' ', '_')
        return f"{username}/{safe_game_name}"
    
    def _navigate_to_save_folder(self, ftp_host: ftputil.FTPHost, username: str, game_name: str, 
                                  folder_number: int) -> str:
        """Navigate to a specific save folder, creating directories if needed"""
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
                print(f"INFO: Created save folder: {save_folder_name}")
            except Exception as e:
                # Might already exist, try to navigate
                if not ftp_host.path.exists(save_folder_path):
                    print(f"ERROR: Failed to create save folder {save_folder_name}: {e}")
                    raise
        
        # Navigate to save folder
        ftp_host.chdir(save_folder_path)
        print(f"DEBUG: Navigated to save folder: {save_folder_path}")
        
        return save_folder_path
    
    def create_directory(self, username: str, game_name: str, folder_number: int, 
                        remote_dir_path: str) -> Tuple[bool, str]:
        """Create a directory structure on FTP server (for empty directories)"""
        ftp_host = None
        try:
            ftp_host = self._get_connection()
            save_folder_path = self._navigate_to_save_folder(ftp_host, username, game_name, folder_number)
            
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
                        print(f"INFO: Created directory structure: {full_dir_path}")
                    except Exception as e:
                        print(f"ERROR: Failed to create directory structure: {e}")
                        return False, f"Failed to create directory structure: {str(e)}"
            else:
                # Single directory name
                full_dir_path = ftp_host.path.join(save_folder_path, remote_dir_path)
                if not ftp_host.path.exists(full_dir_path):
                    try:
                        ftp_host.mkdir(remote_dir_path)
                        print(f"INFO: Created empty directory: {full_dir_path}")
                    except Exception as e:
                        print(f"WARNING: Could not create directory {remote_dir_path}: {e}")
                        return False, f"Failed to create directory: {str(e)}"
            
            print(f"INFO: Successfully created directory structure: {full_dir_path}")
            return True, f"Directory created: {full_dir_path}"
            
        except Exception as e:
            print(f"ERROR: Failed to create directory: {e}")
            return False, f"Failed to create directory: {str(e)}"
        finally:
            if ftp_host:
                ftp_host.close()
    
    def upload_save(self, username: str, game_name: str, local_file_path: str, 
                   folder_number: int, remote_filename: Optional[str] = None) -> Tuple[bool, str]:
        """Upload a save file to FTP server - 1:1 binary transfer, preserves exact directory structure"""
        if not os.path.exists(local_file_path):
            return False, f"Local file not found: {local_file_path}"
        
        if remote_filename is None:
            remote_filename = os.path.basename(local_file_path)
        
        ftp_host = None
        try:
            ftp_host = self._get_connection()
            save_folder_path = self._navigate_to_save_folder(ftp_host, username, game_name, folder_number)
            
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
                    if not ftp_host.path.exists(dir_path):
                        try:
                            ftp_host.makedirs(dir_path)
                            print(f"DEBUG: Created directory structure: {dir_path}")
                        except Exception as e:
                            print(f"ERROR: Failed to create directory structure: {e}")
                            return False, f"Failed to create directory structure: {str(e)}"
                    ftp_host.chdir(dir_path)
                
                # Use only the filename (last part)
                remote_filename = path_parts[-1]
            else:
                # Ensure we're in the save folder
                ftp_host.chdir(save_folder_path)
            
            # Build full remote path
            full_remote_path = ftp_host.path.join(ftp_host.getcwd(), remote_filename)
            
            print(f"DEBUG: Current FTP directory: {ftp_host.getcwd()}, uploading: {remote_filename}")
            
            # Check if file exists and delete it first to ensure overwrite
            if ftp_host.path.exists(full_remote_path) and ftp_host.path.isfile(full_remote_path):
                try:
                    ftp_host.remove(full_remote_path)
                    print(f"DEBUG: Deleted existing file: {remote_filename}")
                except Exception as e:
                    print(f"WARNING: Could not delete existing file {remote_filename}: {e}")
            
            # Upload file using ftputil
            ftp_host.upload(local_file_path, remote_filename)
            
            print(f"INFO: Successfully uploaded {remote_filename} to {full_remote_path}")
            return True, f"File uploaded successfully to {full_remote_path}"
            
        except Exception as e:
            print(f"ERROR: Failed to upload save file: {e}")
            return False, f"Upload failed: {str(e)}"
        finally:
            if ftp_host:
                ftp_host.close()
    
    def download_save(self, username: str, game_name: str, remote_filename: str, 
                     local_file_path: str, folder_number: int) -> Tuple[bool, str]:
        """Download a save file from FTP server - 1:1 binary transfer, no modifications"""
        ftp_host = None
        try:
            ftp_host = self._get_connection()
            save_folder_path = self._navigate_to_save_folder(ftp_host, username, game_name, folder_number)
            
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
                        print(f"ERROR: Directory not found: {dir_path}")
                        return False, f"Directory not found: {dir_path}"
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
                print(f"ERROR: File not found: {remote_filename} in {save_folder_path}")
                return False, f"File not found: {remote_filename} in {save_folder_path}"
            
            print(f"INFO: Downloading file: {remote_filename} from {save_folder_path}")
            
            # Download file using ftputil
            ftp_host.download(remote_filename, local_file_path)
            
            print(f"INFO: Successfully downloaded {remote_filename} from {save_folder_path}")
            return True, f"File downloaded successfully from {save_folder_path}/{remote_filename}"
            
        except Exception as e:
            print(f"ERROR: Failed to download save file: {e}")
            return False, f"Download failed: {str(e)}"
        finally:
            if ftp_host:
                ftp_host.close()
    
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
                    except Exception as e:
                        print(f"WARNING: Could not list subdirectory {item_path}: {e}")
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
        except Exception as e:
            print(f"ERROR: Error listing directory {current_path}: {e}")
        
        return files, directories
    
    def list_saves(self, username: str, game_name: str, 
                  folder_number: int) -> Tuple[bool, List[dict], List[str], str]:
        """List all save files and directories recursively in a specific save folder"""
        ftp_host = None
        try:
            ftp_host = self._get_connection()
            save_folder_path = self._navigate_to_save_folder(ftp_host, username, game_name, folder_number)
            print(f"INFO: Listing files recursively in: {save_folder_path}")
            
            # Recursively list all files and directories
            all_files, all_directories = self._list_recursive(ftp_host, save_folder_path, '.')
            
            print(f"INFO: Found {len(all_files)} file(s) and {len(all_directories)} directory(ies)")
            return True, all_files, all_directories, f"Found {len(all_files)} file(s) and {len(all_directories)} directory(ies)"
            
        except Exception as e:
            print(f"ERROR: Failed to list save files: {e}")
            return False, [], [], f"List failed: {str(e)}"
        finally:
            if ftp_host:
                ftp_host.close()
