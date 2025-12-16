"""
Standalone FTP Client Worker
Simplified to only handle file operations - folder tracking is done in Django models
"""
import os
import ftplib
from pathlib import Path
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


class FTPClient:
    """Simplified FTP client - only handles file operations, no folder management"""
    
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
    
    def _get_connection(self) -> ftplib.FTP:
        """Create and return an FTP connection"""
        try:
            ftp = ftplib.FTP()
            ftp.connect(self.host, self.port, timeout=self.timeout)
            ftp.login(self.username, self.password)
            ftp.set_pasv(True)  # Use passive mode for better compatibility
            return ftp
        except Exception as e:
            logger.error(f"Failed to connect to FTP server: {e}")
            raise
    
    def _ensure_directory_exists(self, ftp: ftplib.FTP, path: str) -> None:
        """Ensure a directory path exists on FTP server, creating it if necessary"""
        # Go to root first
        try:
            ftp.cwd('/')
        except:
            pass
        
        parts = path.strip('/').split('/')
        
        for part in parts:
            if not part:
                continue
            
            # Try to change into the directory
            try:
                ftp.cwd(part)
                logger.debug(f"Directory exists: {part}")
            except ftplib.error_perm:
                # Directory doesn't exist, create it (relative to current directory)
                try:
                    ftp.mkd(part)
                    logger.info(f"Created FTP directory: {part}")
                    # Change into the newly created directory
                    try:
                        ftp.cwd(part)
                    except ftplib.error_perm as e:
                        logger.error(f"Failed to change into newly created directory {part}: {e}")
                        raise
                except ftplib.error_perm as e:
                    # Directory might have been created by another process, try to change into it
                    try:
                        ftp.cwd(part)
                    except ftplib.error_perm:
                        logger.error(f"Failed to create/access directory {part}: {e}")
                        raise
    
    def _get_user_game_path(self, username: str, game_name: str) -> str:
        """Get the base path for a user's game on FTP server"""
        safe_game_name = "".join(c for c in game_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_game_name = safe_game_name.replace(' ', '_')
        return f"{username}/{safe_game_name}"
    
    def _navigate_to_save_folder(self, ftp: ftplib.FTP, username: str, game_name: str, 
                                  folder_number: int) -> str:
        """Navigate to a specific save folder, creating directories if needed"""
        base_path = self._get_user_game_path(username, game_name)
        save_folder_name = f"save_{folder_number}"
        save_folder_path = f"{base_path}/{save_folder_name}"
        
        # Ensure base path exists
        self._ensure_directory_exists(ftp, base_path)
        
        # Navigate to save folder (create if doesn't exist)
        try:
            ftp.cwd(save_folder_name)
            logger.debug(f"Save folder exists: {save_folder_name}")
        except ftplib.error_perm:
            try:
                ftp.mkd(save_folder_name)
                logger.info(f"Created save folder: {save_folder_name}")
                ftp.cwd(save_folder_name)
            except ftplib.error_perm as e:
                # Try to change into it in case it was created by another process
                try:
                    ftp.cwd(save_folder_name)
                except ftplib.error_perm:
                    logger.error(f"Failed to create/access save folder {save_folder_name}: {e}")
                    raise
        
        return save_folder_path
    
    def create_directory(self, username: str, game_name: str, folder_number: int, 
                        remote_dir_path: str) -> Tuple[bool, str]:
        """Create a directory structure on FTP server (for empty directories)"""
        ftp = None
        try:
            ftp = self._get_connection()
            save_folder_path = self._navigate_to_save_folder(ftp, username, game_name, folder_number)
            
            # Handle nested paths: create directory structure
            if '/' in remote_dir_path or '\\' in remote_dir_path:
                # Normalize to forward slashes
                path_parts = remote_dir_path.replace('\\', '/').split('/')
                # Filter out empty parts
                path_parts = [p for p in path_parts if p]
                
                # Create directory structure
                for dir_name in path_parts:
                    try:
                        # Try to change into the directory
                        ftp.cwd(dir_name)
                        logger.debug(f"Directory exists: {dir_name}")
                    except ftplib.error_perm:
                        # Directory doesn't exist, create it
                        try:
                            ftp.mkd(dir_name)
                            logger.info(f"Created empty directory: {dir_name}")
                            ftp.cwd(dir_name)
                        except ftplib.error_perm as e:
                            # Directory might have been created by another process, try to change into it
                            try:
                                ftp.cwd(dir_name)
                                logger.debug(f"Directory was created by another process: {dir_name}")
                            except ftplib.error_perm:
                                logger.error(f"Failed to create/access directory {dir_name}: {e}")
                                return False, f"Failed to create directory structure: {str(e)}"
            else:
                # Single directory name
                try:
                    ftp.cwd(remote_dir_path)
                    logger.debug(f"Directory exists: {remote_dir_path}")
                except ftplib.error_perm:
                    try:
                        ftp.mkd(remote_dir_path)
                        logger.info(f"Created empty directory: {remote_dir_path}")
                    except ftplib.error_perm as e:
                        logger.warning(f"Could not create directory {remote_dir_path}: {e}")
                        return False, f"Failed to create directory: {str(e)}"
            
            full_remote_path = f"{save_folder_path}/{remote_dir_path}"
            logger.info(f"Successfully created directory structure: {full_remote_path}")
            return True, f"Directory created: {full_remote_path}"
            
        except Exception as e:
            logger.error(f"Failed to create directory: {e}")
            return False, f"Failed to create directory: {str(e)}"
        finally:
            if ftp:
                try:
                    ftp.quit()
                except:
                    ftp.close()
    
    def upload_save(self, username: str, game_name: str, local_file_path: str, 
                   folder_number: int, remote_filename: Optional[str] = None) -> Tuple[bool, str]:
        """Upload a save file to FTP server - 1:1 binary transfer, preserves exact directory structure"""
        if not os.path.exists(local_file_path):
            return False, f"Local file not found: {local_file_path}"
        
        if remote_filename is None:
            remote_filename = os.path.basename(local_file_path)
        
        ftp = None
        try:
            ftp = self._get_connection()
            save_folder_path = self._navigate_to_save_folder(ftp, username, game_name, folder_number)
            current_path = save_folder_path
            
            # Handle nested paths: if remote_filename contains path separators, create directory structure
            if '/' in remote_filename or '\\' in remote_filename:
                # Normalize to forward slashes
                path_parts = remote_filename.replace('\\', '/').split('/')
                # Filter out empty parts
                path_parts = [p for p in path_parts if p]
                
                # Create directory structure (all parts except the filename)
                for i in range(len(path_parts) - 1):
                    dir_name = path_parts[i]
                    try:
                        # Try to change into the directory
                        ftp.cwd(dir_name)
                        logger.debug(f"Directory exists: {dir_name}")
                        current_path += f"/{dir_name}"
                    except ftplib.error_perm:
                        # Directory doesn't exist, create it
                        try:
                            ftp.mkd(dir_name)
                            logger.info(f"Created directory: {dir_name}")
                            ftp.cwd(dir_name)
                            current_path += f"/{dir_name}"
                        except ftplib.error_perm as e:
                            # Directory might have been created by another process, try to change into it
                            try:
                                ftp.cwd(dir_name)
                                logger.debug(f"Directory was created by another process: {dir_name}")
                                current_path += f"/{dir_name}"
                            except ftplib.error_perm:
                                logger.error(f"Failed to create/access directory {dir_name}: {e}")
                                return False, f"Failed to create directory structure: {str(e)}"
                
                # Use only the filename (last part) for STOR command
                remote_filename = path_parts[-1]
            
            logger.debug(f"Current FTP directory: {ftp.pwd()}, uploading: {remote_filename}")
            
            # Check if file exists and delete it first to ensure overwrite
            try:
                # Try to delete the file if it exists (this will fail silently if it doesn't exist)
                ftp.delete(remote_filename)
                logger.debug(f"Deleted existing file: {remote_filename}")
            except ftplib.error_perm:
                # File doesn't exist, that's fine - we'll create it
                logger.debug(f"File does not exist yet: {remote_filename}")
            except Exception as e:
                # Other errors are logged but don't stop the upload
                logger.warning(f"Could not delete existing file {remote_filename}: {e}")
            
            # Binary upload - 1:1 transfer, no modifications (overwrites if file exists)
            with open(local_file_path, 'rb') as local_file:
                ftp.storbinary(f'STOR {remote_filename}', local_file)
            
            full_remote_path = f"{current_path}/{remote_filename}"
            logger.info(f"Successfully uploaded {remote_filename} to {full_remote_path}")
            return True, f"File uploaded successfully to {full_remote_path}"
            
        except Exception as e:
            logger.error(f"Failed to upload save file: {e}")
            return False, f"Upload failed: {str(e)}"
        finally:
            if ftp:
                try:
                    ftp.quit()
                except:
                    ftp.close()
    
    def download_save(self, username: str, game_name: str, remote_filename: str, 
                     local_file_path: str, folder_number: int) -> Tuple[bool, str]:
        """Download a save file from FTP server - 1:1 binary transfer, no modifications"""
        ftp = None
        try:
            ftp = self._get_connection()
            save_folder_path = self._navigate_to_save_folder(ftp, username, game_name, folder_number)
            
            # Handle nested paths: if remote_filename contains path separators, navigate to directory
            if '/' in remote_filename or '\\' in remote_filename:
                # Normalize to forward slashes
                path_parts = remote_filename.replace('\\', '/').split('/')
                # Filter out empty parts
                path_parts = [p for p in path_parts if p]
                
                # Navigate to directory structure (all parts except the filename)
                for i in range(len(path_parts) - 1):
                    dir_name = path_parts[i]
                    try:
                        ftp.cwd(dir_name)
                        logger.debug(f"Navigated to directory: {dir_name}")
                    except ftplib.error_perm as e:
                        logger.error(f"Failed to navigate to directory {dir_name}: {e}")
                        return False, f"Directory not found: {dir_name}"
                
                # Use only the filename (last part) for RETR command
                remote_filename = path_parts[-1]
            
            # Verify file exists and get exact filename (in case of spaces)
            files = []
            ftp.retrlines('LIST', files.append)
            exact_filename = None
            for file_info in files:
                if not file_info.startswith('d'):
                    parts = file_info.split()
                    if len(parts) >= 9:
                        # Get filename handling spaces correctly
                        filename = ' '.join(parts[8:]) if len(parts) > 8 else parts[-1]
                        if filename == remote_filename:
                            exact_filename = filename
                            break
            
            if not exact_filename:
                logger.error(f"File not found: {remote_filename} in {save_folder_path}")
                logger.debug(f"Available files: {[f for f in files if not f.startswith('d')]}")
                return False, f"File not found: {remote_filename} in {save_folder_path}"
            
            logger.info(f"Downloading file: {exact_filename} from {save_folder_path}")
            # Binary download - 1:1 transfer, no modifications
            with open(local_file_path, 'wb') as local_file:
                ftp.retrbinary(f'RETR {exact_filename}', local_file.write)
            
            logger.info(f"Successfully downloaded {remote_filename} from {save_folder_path}")
            return True, f"File downloaded successfully from {save_folder_path}/{remote_filename}"
            
        except Exception as e:
            logger.error(f"Failed to download save file: {e}")
            return False, f"Download failed: {str(e)}"
        finally:
            if ftp:
                try:
                    ftp.quit()
                except:
                    ftp.close()
    
    def _list_recursive(self, ftp: ftplib.FTP, base_path: str, current_path: str = '') -> Tuple[List[dict], List[str]]:
        """Recursively list all files and directories from FTP"""
        files = []
        directories = []
        
        try:
            # List current directory
            items = []
            ftp.retrlines('LIST', items.append)
            
            for item in items:
                if item.startswith('d'):
                    # It's a directory
                    parts = item.split()
                    if len(parts) >= 9:
                        dir_name = ' '.join(parts[8:]) if len(parts) > 8 else parts[-1]
                        # Skip . and ..
                        if dir_name in ('.', '..'):
                            continue
                        
                        full_dir_path = f"{current_path}/{dir_name}" if current_path else dir_name
                        directories.append(full_dir_path)
                        
                        # Recursively list subdirectory
                        try:
                            ftp.cwd(dir_name)
                            sub_files, sub_dirs = self._list_recursive(ftp, base_path, full_dir_path)
                            files.extend(sub_files)
                            directories.extend(sub_dirs)
                            ftp.cwd('..')
                        except Exception as e:
                            logger.warning(f"Could not list subdirectory {dir_name}: {e}")
                else:
                    # It's a file
                    parts = item.split()
                    if len(parts) >= 9:
                        filename = ' '.join(parts[8:]) if len(parts) > 8 else parts[-1]
                        try:
                            size = int(parts[4])
                        except (ValueError, IndexError):
                            size = 0
                        
                        full_file_path = f"{current_path}/{filename}" if current_path else filename
                        files.append({
                            'name': full_file_path,
                            'size': size
                        })
        except Exception as e:
            logger.error(f"Error listing directory {current_path}: {e}")
        
        return files, directories
    
    def list_saves(self, username: str, game_name: str, 
                  folder_number: int) -> Tuple[bool, List[dict], List[str], str]:
        """List all save files and directories recursively in a specific save folder"""
        ftp = None
        try:
            ftp = self._get_connection()
            save_folder_path = self._navigate_to_save_folder(ftp, username, game_name, folder_number)
            logger.info(f"Listing files recursively in: {save_folder_path}")
            
            # Recursively list all files and directories
            all_files, all_directories = self._list_recursive(ftp, save_folder_path)
            
            logger.info(f"Found {len(all_files)} file(s) and {len(all_directories)} directory(ies)")
            return True, all_files, all_directories, f"Found {len(all_files)} file(s) and {len(all_directories)} directory(ies)"
            
        except Exception as e:
            logger.error(f"Failed to list save files: {e}")
            return False, [], [], f"List failed: {str(e)}"
        finally:
            if ftp:
                try:
                    ftp.quit()
                except:
                    ftp.close()
