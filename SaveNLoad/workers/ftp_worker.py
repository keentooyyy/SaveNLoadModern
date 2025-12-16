"""
FTP Worker for managing save files on FTP server.

Directory structure:
    ftp_home / username / game_name / save_folder_1-10 / actual_saves

Each game can have a maximum of 10 save folders.
"""
import os
import ftplib
from pathlib import Path
from typing import Optional, List, Tuple
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class FTPWorker:
    """Worker class for managing save files on FTP server"""
    
    MAX_SAVE_FOLDERS = 10
    
    def __init__(self):
        """Initialize FTP connection settings from environment variables"""
        self.host = getattr(settings, 'FTP_HOST', '192.168.88.101')
        self.port = getattr(settings, 'FTP_PORT', 21)
        self.username = getattr(settings, 'FTP_USERNAME', None)
        self.password = getattr(settings, 'FTP_PASSWORD', None)
        self.timeout = getattr(settings, 'FTP_TIMEOUT', 30)
        
        if not self.username or not self.password:
            raise ValueError("FTP_USERNAME and FTP_PASSWORD must be set in environment variables")
    
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
        parts = path.strip('/').split('/')
        current_path = ''
        
        for part in parts:
            if not part:
                continue
            current_path = f"{current_path}/{part}" if current_path else part
            
            try:
                # Try to change to directory (will fail if it doesn't exist)
                ftp.cwd(current_path)
            except ftplib.error_perm:
                # Directory doesn't exist, create it
                try:
                    ftp.mkd(current_path)
                    logger.info(f"Created FTP directory: {current_path}")
                except ftplib.error_perm as e:
                    # Directory might have been created by another process
                    # Try to change to it again
                    try:
                        ftp.cwd(current_path)
                    except ftplib.error_perm:
                        logger.error(f"Failed to create/access directory {current_path}: {e}")
                        raise
    
    def _get_user_game_path(self, username: str, game_name: str) -> str:
        """Get the base path for a user's game on FTP server"""
        # Sanitize game name for filesystem (remove invalid characters)
        safe_game_name = "".join(c for c in game_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_game_name = safe_game_name.replace(' ', '_')
        return f"{username}/{safe_game_name}"
    
    def _get_save_folders(self, ftp: ftplib.FTP, base_path: str) -> List[str]:
        """Get list of existing save folders for a game"""
        try:
            ftp.cwd(base_path)
            items = []
            ftp.retrlines('LIST', items.append)
            
            save_folders = []
            for item in items:
                # Parse LIST output (format varies by server, but typically starts with 'd' for directories)
                if item.startswith('d'):
                    parts = item.split()
                    if len(parts) >= 9:
                        folder_name = parts[-1]
                        # Check if it's a save folder (save_1, save_2, etc.)
                        if folder_name.startswith('save_') and folder_name[5:].isdigit():
                            save_folders.append(folder_name)
            
            # Sort by number
            save_folders.sort(key=lambda x: int(x.split('_')[1]))
            return save_folders
        except ftplib.error_perm:
            # Directory doesn't exist yet
            return []
    
    def _get_next_save_folder(self, ftp: ftplib.FTP, base_path: str) -> str:
        """Get the next available save folder number, creating a new one if needed"""
        save_folders = self._get_save_folders(ftp, base_path)
        
        if len(save_folders) >= self.MAX_SAVE_FOLDERS:
            # Use the oldest folder (first one) and rotate
            oldest_folder = save_folders[0]
            # Delete all files in the oldest folder to reuse it
            try:
                ftp.cwd(f"{base_path}/{oldest_folder}")
                files = []
                ftp.retrlines('LIST', files.append)
                for file_info in files:
                    if not file_info.startswith('d'):  # Only delete files, not directories
                        parts = file_info.split()
                        if len(parts) >= 9:
                            filename = parts[-1]
                            try:
                                ftp.delete(filename)
                            except Exception as e:
                                logger.warning(f"Failed to delete file {filename}: {e}")
                ftp.cwd('..')
                return oldest_folder
            except Exception as e:
                logger.error(f"Failed to clear oldest save folder: {e}")
                # Fall through to create new folder anyway
        
        # Find the next available number
        if not save_folders:
            next_num = 1
        else:
            # Get the highest number and add 1
            highest_num = max(int(folder.split('_')[1]) for folder in save_folders)
            next_num = highest_num + 1
        
        folder_name = f"save_{next_num}"
        return folder_name
    
    def _get_or_create_save_folder(self, ftp: ftplib.FTP, username: str, game_name: str) -> str:
        """Get or create a save folder for a game, ensuring max 10 folders limit"""
        base_path = self._get_user_game_path(username, game_name)
        
        # Ensure base path exists
        self._ensure_directory_exists(ftp, base_path)
        
        # Get next save folder
        save_folder_name = self._get_next_save_folder(ftp, base_path)
        save_folder_path = f"{base_path}/{save_folder_name}"
        
        # Ensure save folder exists
        self._ensure_directory_exists(ftp, save_folder_path)
        
        return save_folder_path
    
    def upload_save(self, username: str, game_name: str, local_file_path: str, 
                   remote_filename: Optional[str] = None) -> Tuple[bool, str]:
        """
        Upload a save file to FTP server.
        
        Args:
            username: The username (will create folder if doesn't exist)
            game_name: The game name (will create folder if doesn't exist)
            local_file_path: Path to the local file to upload
            remote_filename: Optional custom filename on FTP (defaults to local filename)
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not os.path.exists(local_file_path):
            return False, f"Local file not found: {local_file_path}"
        
        if remote_filename is None:
            remote_filename = os.path.basename(local_file_path)
        
        ftp = None
        try:
            ftp = self._get_connection()
            
            # Get or create save folder
            save_folder_path = self._get_or_create_save_folder(ftp, username, game_name)
            
            # Change to save folder
            ftp.cwd(save_folder_path)
            
            # Upload file
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
                     local_file_path: str, save_folder_number: Optional[int] = None) -> Tuple[bool, str]:
        """
        Download a save file from FTP server.
        
        Args:
            username: The username
            game_name: The game name
            remote_filename: Name of the file on FTP server
            local_file_path: Where to save the file locally
            save_folder_number: Optional specific save folder number (1-10). 
                               If None, downloads from the most recent folder.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        ftp = None
        try:
            ftp = self._get_connection()
            
            base_path = self._get_user_game_path(username, game_name)
            
            # Determine which save folder to use
            if save_folder_number:
                save_folder_name = f"save_{save_folder_number}"
                save_folder_path = f"{base_path}/{save_folder_name}"
            else:
                # Get the most recent save folder
                save_folders = self._get_save_folders(ftp, base_path)
                if not save_folders:
                    return False, f"No save folders found for {username}/{game_name}"
                save_folder_name = save_folders[-1]  # Most recent (last in sorted list)
                save_folder_path = f"{base_path}/{save_folder_name}"
            
            # Change to save folder
            try:
                ftp.cwd(save_folder_path)
            except ftplib.error_perm:
                return False, f"Save folder not found: {save_folder_path}"
            
            # Check if file exists
            files = []
            ftp.retrlines('LIST', files.append)
            file_exists = any(remote_filename in item for item in files if not item.startswith('d'))
            
            if not file_exists:
                return False, f"File not found: {remote_filename} in {save_folder_path}"
            
            # Download file
            with open(local_file_path, 'wb') as local_file:
                ftp.retrbinary(f'RETR {remote_filename}', local_file.write)
            
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
                  save_folder_number: Optional[int] = None) -> Tuple[bool, List[dict], str]:
        """
        List all save files for a user's game.
        
        Args:
            username: The username
            game_name: The game name
            save_folder_number: Optional specific save folder number (1-10).
                               If None, lists all save folders.
        
        Returns:
            Tuple of (success: bool, files: List[dict], message: str)
            Each dict contains: {'name': str, 'size': int, 'folder': str}
        """
        ftp = None
        try:
            ftp = self._get_connection()
            
            base_path = self._get_user_game_path(username, game_name)
            
            # Get save folders to check
            if save_folder_number:
                save_folders = [f"save_{save_folder_number}"]
            else:
                save_folders = self._get_save_folders(ftp, base_path)
                if not save_folders:
                    return True, [], f"No save folders found for {username}/{game_name}"
            
            all_files = []
            for save_folder in save_folders:
                save_folder_path = f"{base_path}/{save_folder}"
                try:
                    ftp.cwd(save_folder_path)
                    files = []
                    ftp.retrlines('LIST', files.append)
                    
                    for file_info in files:
                        if not file_info.startswith('d'):  # Only files, not directories
                            parts = file_info.split()
                            if len(parts) >= 9:
                                filename = parts[-1]
                                # Try to parse file size (usually around index 4)
                                try:
                                    size = int(parts[4])
                                except (ValueError, IndexError):
                                    size = 0
                                
                                all_files.append({
                                    'name': filename,
                                    'size': size,
                                    'folder': save_folder
                                })
                except ftplib.error_perm:
                    continue
            
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
    
    def delete_save(self, username: str, game_name: str, remote_filename: str,
                   save_folder_number: Optional[int] = None) -> Tuple[bool, str]:
        """
        Delete a save file from FTP server.
        
        Args:
            username: The username
            game_name: The game name
            remote_filename: Name of the file to delete
            save_folder_number: Optional specific save folder number (1-10).
                               If None, searches all folders.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        ftp = None
        try:
            ftp = self._get_connection()
            
            base_path = self._get_user_game_path(username, game_name)
            
            # Determine which save folder to check
            if save_folder_number:
                save_folders = [f"save_{save_folder_number}"]
            else:
                save_folders = self._get_save_folders(ftp, base_path)
            
            for save_folder in save_folders:
                save_folder_path = f"{base_path}/{save_folder}"
                try:
                    ftp.cwd(save_folder_path)
                    # Check if file exists
                    files = []
                    ftp.retrlines('LIST', files.append)
                    file_exists = any(remote_filename in item for item in files if not item.startswith('d'))
                    
                    if file_exists:
                        ftp.delete(remote_filename)
                        logger.info(f"Successfully deleted {remote_filename} from {save_folder_path}")
                        return True, f"File deleted successfully from {save_folder_path}"
                except ftplib.error_perm:
                    continue
            
            return False, f"File not found: {remote_filename}"
            
        except Exception as e:
            logger.error(f"Failed to delete save file: {e}")
            return False, f"Delete failed: {str(e)}"
        finally:
            if ftp:
                try:
                    ftp.quit()
                except:
                    ftp.close()

