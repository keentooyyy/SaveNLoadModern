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
    
    def upload_save(self, username: str, game_name: str, local_file_path: str, 
                   folder_number: int, remote_filename: Optional[str] = None) -> Tuple[bool, str]:
        """Upload a save file to FTP server - 1:1 binary transfer, no modifications"""
        if not os.path.exists(local_file_path):
            return False, f"Local file not found: {local_file_path}"
        
        if remote_filename is None:
            remote_filename = os.path.basename(local_file_path)
        
        ftp = None
        try:
            ftp = self._get_connection()
            save_folder_path = self._navigate_to_save_folder(ftp, username, game_name, folder_number)
            logger.debug(f"Current FTP directory: {ftp.pwd()}, uploading: {remote_filename}")
            
            # Binary upload - 1:1 transfer, no modifications
            with open(local_file_path, 'rb') as local_file:
                ftp.storbinary(f'STOR {remote_filename}', local_file)
            
            logger.info(f"Successfully uploaded {remote_filename} to {save_folder_path}")
            return True, f"File uploaded successfully to {save_folder_path}/{remote_filename}"
            
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
    
    def list_saves(self, username: str, game_name: str, 
                  folder_number: int) -> Tuple[bool, List[dict], str]:
        """List all save files in a specific save folder"""
        ftp = None
        try:
            ftp = self._get_connection()
            save_folder_path = self._navigate_to_save_folder(ftp, username, game_name, folder_number)
            logger.info(f"Listing files in: {save_folder_path}")
            
            files = []
            ftp.retrlines('LIST', files.append)
            logger.info(f"Found {len(files)} items in {save_folder_path}")
            
            all_files = []
            for file_info in files:
                if not file_info.startswith('d'):
                    parts = file_info.split()
                    if len(parts) >= 9:
                        # Filename is everything after the date/time (typically 8 fields before filename)
                        # Format: permissions links owner group size month day time filename
                        # Handle filenames with spaces by joining everything after the 8th field
                        filename = ' '.join(parts[8:]) if len(parts) > 8 else parts[-1]
                        try:
                            size = int(parts[4])
                        except (ValueError, IndexError):
                            size = 0
                        
                        logger.info(f"Found file: {filename} (size: {size})")
                        all_files.append({
                            'name': filename,
                            'size': size
                        })
            
            logger.info(f"Total files found: {len(all_files)}")
            return True, all_files, f"Found {len(all_files)} file(s)"
            
        except Exception as e:
            logger.error(f"Failed to list save files: {e}")
            return False, [], f"List failed: {str(e)}"
        finally:
            if ftp:
                try:
                    ftp.quit()
                except:
                    ftp.close()
