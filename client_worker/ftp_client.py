"""
Standalone FTP Client Worker
This can be used on client PCs without Django dependencies
"""
import os
import ftplib
from pathlib import Path
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


class FTPClient:
    """Standalone FTP client for managing save files on FTP server"""
    
    MAX_SAVE_FOLDERS = 10
    
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
    
    def _get_save_folders(self, ftp: ftplib.FTP, base_path: str) -> List[str]:
        """Get list of existing save folders for a game"""
        try:
            # Make sure we're in the right directory
            try:
                # Go to root first
                ftp.cwd('/')
                logger.info(f"Current directory after root: {ftp.pwd()}")
                
                # Navigate to base path step by step
                parts = base_path.strip('/').split('/')
                for part in parts:
                    if part:
                        ftp.cwd(part)
                        logger.info(f"Changed to: {ftp.pwd()}")
                
                current_dir = ftp.pwd()
                logger.info(f"Final directory: {current_dir} (expected: {base_path})")
            except ftplib.error_perm as e:
                logger.error(f"Cannot access base path: {base_path}, error: {e}")
                return []
            
            items = []
            ftp.retrlines('LIST', items.append)
            
            logger.info(f"LIST output for {base_path} (current dir: {ftp.pwd()}, {len(items)} items):")
            for idx, item in enumerate(items):
                logger.info(f"  [{idx}] {item}")
            
            save_folders = []
            # Get parent directory name to filter it out
            path_parts = base_path.strip('/').split('/')
            parent_dir_name = path_parts[-2] if len(path_parts) > 1 else None
            current_dir_name = path_parts[-1] if path_parts else None
            
            for item in items:
                parts = item.split()
                if not parts:
                    continue
                
                # Get the last part (usually the name)
                potential_name = parts[-1] if parts else ""
                
                # Skip common parent/current directory indicators
                if potential_name in ['.', '..']:
                    logger.debug(f"Skipping parent/current directory entry: {potential_name}")
                    continue
                
                # Skip if it matches the parent directory name (FTP servers sometimes show parent in LIST)
                if parent_dir_name and potential_name == parent_dir_name:
                    logger.debug(f"Skipping parent directory entry: {potential_name}")
                    continue
                
                # Skip if it matches the current directory name (shouldn't happen but just in case)
                if current_dir_name and potential_name == current_dir_name:
                    logger.debug(f"Skipping current directory entry: {potential_name}")
                    continue
                
                # FTP LIST output formats vary by server:
                # Unix: "drwxr-xr-x 2 user group 4096 Dec 16 10:55 save_1"
                # Windows: "12-16-25  10:55AM       <DIR>          save_1"
                # Or: "d---------   1 user group           0 Dec 16 10:55 save_1"
                
                folder_name = None
                is_directory = False
                
                # Check if it's a directory
                if item.startswith('d'):
                    is_directory = True
                elif '<DIR>' in item.upper() or ' <DIR> ' in item.upper():
                    is_directory = True
                
                if is_directory:
                    # Method 1: Unix style - last part is usually the name
                    if len(parts) >= 9:
                        folder_name = parts[-1]
                    # Method 2: Windows style - after <DIR>
                    elif '<DIR>' in item.upper():
                        dir_marker = item.upper().find('<DIR>')
                        after_dir = item[dir_marker + 5:].strip()
                        if after_dir:
                            folder_name = after_dir.split()[0] if after_dir.split() else after_dir
                    # Method 3: Try last part anyway
                    elif parts:
                        folder_name = parts[-1]
                    
                    # Also try searching for "save_" pattern in the entire line
                    if not folder_name or not folder_name.startswith('save_'):
                        for part in parts:
                            if part.startswith('save_') and len(part) > 5:
                                if part[5:].isdigit():
                                    folder_name = part
                                    break
                
                # Validate it's a save folder
                if folder_name and folder_name.startswith('save_'):
                    try:
                        folder_num = folder_name[5:]  # Everything after "save_"
                        if folder_num.isdigit():
                            save_folders.append(folder_name)
                            logger.info(f"Found save folder: {folder_name}")
                    except Exception as e:
                        logger.debug(f"Invalid save folder name: {folder_name}, error: {e}")
            
            save_folders.sort(key=lambda x: int(x.split('_')[1]) if len(x.split('_')) > 1 and x.split('_')[1].isdigit() else 0)
            logger.info(f"Total save folders found: {len(save_folders)} - {save_folders}")
            return save_folders
        except ftplib.error_perm as e:
            logger.error(f"Permission error accessing {base_path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting save folders from {base_path}: {e}", exc_info=True)
            return []
    
    def _get_next_save_folder(self, ftp: ftplib.FTP, base_path: str) -> str:
        """Get the next available save folder number, creating a new one if needed"""
        save_folders = self._get_save_folders(ftp, base_path)
        
        if len(save_folders) >= self.MAX_SAVE_FOLDERS:
            oldest_folder = save_folders[0]
            try:
                ftp.cwd(f"{base_path}/{oldest_folder}")
                files = []
                ftp.retrlines('LIST', files.append)
                for file_info in files:
                    if not file_info.startswith('d'):
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
        
        if not save_folders:
            next_num = 1
        else:
            highest_num = max(int(folder.split('_')[1]) for folder in save_folders)
            next_num = highest_num + 1
        
        folder_name = f"save_{next_num}"
        return folder_name
    
    def _get_or_create_save_folder(self, ftp: ftplib.FTP, username: str, game_name: str) -> str:
        """Get or create a save folder for a game"""
        base_path = self._get_user_game_path(username, game_name)
        self._ensure_directory_exists(ftp, base_path)
        
        save_folder_name = self._get_next_save_folder(ftp, base_path)
        # Create save folder relative to current directory (we're already in base_path)
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
        
        # Return absolute path for reference
        save_folder_path = f"{base_path}/{save_folder_name}"
        return save_folder_path
    
    def upload_save(self, username: str, game_name: str, local_file_path: str, 
                   remote_filename: Optional[str] = None) -> Tuple[bool, str]:
        """Upload a save file to FTP server"""
        if not os.path.exists(local_file_path):
            return False, f"Local file not found: {local_file_path}"
        
        if remote_filename is None:
            remote_filename = os.path.basename(local_file_path)
        
        ftp = None
        try:
            ftp = self._get_connection()
            save_folder_path = self._get_or_create_save_folder(ftp, username, game_name)
            # _get_or_create_save_folder already navigates us into the save folder, so we're ready to upload
            logger.debug(f"Current FTP directory: {ftp.pwd()}, uploading to: {remote_filename}")
            
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
        """Download a save file from FTP server"""
        ftp = None
        try:
            ftp = self._get_connection()
            base_path = self._get_user_game_path(username, game_name)
            
            # Navigate to base_path first
            self._ensure_directory_exists(ftp, base_path)
            
            if save_folder_number:
                save_folder_name = f"save_{save_folder_number}"
            else:
                save_folders = self._get_save_folders(ftp, base_path)
                if not save_folders:
                    return False, f"No save folders found for {username}/{game_name}"
                save_folder_name = save_folders[-1]
            
            save_folder_path = f"{base_path}/{save_folder_name}"
            
            # Navigate to save folder relative to current directory (we're already in base_path)
            try:
                ftp.cwd(save_folder_name)
            except ftplib.error_perm:
                return False, f"Save folder not found: {save_folder_path}"
            
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
                  save_folder_number: Optional[int] = None) -> Tuple[bool, List[dict], str]:
        """List all save files for a user's game"""
        ftp = None
        try:
            ftp = self._get_connection()
            base_path = self._get_user_game_path(username, game_name)
            logger.info(f"Listing saves for path: {base_path}")
            
            if save_folder_number:
                save_folders = [f"save_{save_folder_number}"]
                logger.info(f"Using specific save folder: save_{save_folder_number}")
            else:
                save_folders = self._get_save_folders(ftp, base_path)
                logger.info(f"Found {len(save_folders)} save folder(s): {save_folders}")
                if not save_folders:
                    return True, [], f"No save folders found for {username}/{game_name}"
            
            # Ensure we're in base_path (we should be after _get_save_folders, but just in case)
            self._ensure_directory_exists(ftp, base_path)
            
            all_files = []
            # We're already in base_path after _get_save_folders, so navigate to save folders relative to current directory
            for save_folder in save_folders:
                save_folder_path = f"{base_path}/{save_folder}"
                logger.info(f"Checking save folder: {save_folder_path}")
                try:
                    # Navigate to save folder relative to current directory (we're already in base_path)
                    ftp.cwd(save_folder)
                    files = []
                    ftp.retrlines('LIST', files.append)
                    logger.info(f"Found {len(files)} items in {save_folder_path}")
                    
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
                                    'size': size,
                                    'folder': save_folder
                                })
                    
                    # Go back to base_path for next iteration
                    ftp.cwd('..')
                except ftplib.error_perm as e:
                    logger.error(f"Permission error accessing {save_folder_path}: {e}")
                    # Try to go back to base_path even if there was an error
                    try:
                        self._ensure_directory_exists(ftp, base_path)
                    except:
                        pass
                    continue
            
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

