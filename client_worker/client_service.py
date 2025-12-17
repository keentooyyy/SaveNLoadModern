"""
Client Worker Service
Runs on client PC to handle save/load operations with proper permissions
"""
import os
import sys
import json
import time
import requests
import webbrowser
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
from dotenv import load_dotenv
from ftp_client import FTPClient

# Load environment variables
load_dotenv()


class ClientWorkerService:
    """Service that runs on client PC to handle save/load operations"""
    
    def __init__(self, server_url: str, poll_interval: int = 5):
        """
        Initialize client worker service
        
        Args:
            server_url: Base URL of the Django server
            poll_interval: How often to poll for pending operations (seconds)
        """
        # Add http:// scheme if missing
        if not server_url.startswith(('http://', 'https://')):
            server_url = f'http://{server_url}'
        # Add default port if no port specified
        if '://' in server_url:
            scheme, rest = server_url.split('://', 1)
            if ':' not in rest.split('/')[0]:  # No port in hostname
                # Default to port 8000 for Django
                host = rest.split('/')[0]
                path = rest[len(host):] if len(rest) > len(host) else ''
                server_url = f'{scheme}://{host}:8000{path}'
        self.server_url = server_url.rstrip('/')
        self.poll_interval = poll_interval
        self.session = requests.Session()
        self.running = False
        self._heartbeat_thread = None
        self._current_client_id = None
        
        
        # Setup FTP client
        ftp_host = os.getenv('FTP_HOST')
        ftp_port = int(os.getenv('FTP_PORT', '21'))
        ftp_username = os.getenv('FTP_USERNAME')
        ftp_password = os.getenv('FTP_PASSWORD')
        
        if not all([ftp_host, ftp_username, ftp_password]):
            raise ValueError("FTP credentials must be set in environment variables")
        
        self.ftp_client = FTPClient(
            host=ftp_host,
            port=ftp_port,
            username=ftp_username,
            password=ftp_password
        )
        
        print("Client Worker Service ready")
    
    def _update_progress(self, operation_id: int, current: int, total: int, message: str = ''):
        """Send progress update to server"""
        try:
            self.session.post(
                f"{self.server_url}/api/client/progress/{operation_id}/",
                json={
                    'current': current,
                    'total': total,
                    'message': message
                },
                timeout=2
            )
        except Exception:
            pass  # Silently fail - progress updates are not critical
    
    def check_permissions(self) -> bool:
        """Check if we have necessary permissions to access files"""
        try:
            # Try to access user's Documents folder (common save location)
            test_path = Path.home() / 'Documents'
            if test_path.exists():
                test_path.stat()  # This will raise if no permission
            return True
        except PermissionError:
            print("Warning: Insufficient file permissions")
            return False
    
    
    def save_game(self, game_id: int, local_save_path: str, 
                 username: str, game_name: str, save_folder_number: int, ftp_path: Optional[str] = None,
                 operation_id: Optional[int] = None) -> Dict[str, Any]:
        """Save game - backup from local PC to FTP"""
        print(f"Backing up save files...")
        
        if not os.path.exists(local_save_path):
            return {
                'success': False,
                'error': 'Oops! You don\'t have any save files to save. Maybe you haven\'t played the game yet, or the save location is incorrect.'
            }
        
        try:
            if os.path.isdir(local_save_path):
                uploaded_files = []
                failed_files = []
                
                # Streaming approach: collect files on-demand as workers become available
                # Like FileZilla - starts uploading immediately, collects more files as workers finish
                print("Starting upload (collecting files on-demand)...")
                
                # Queue for files to be uploaded (buffer up to 100 files ahead)
                file_queue = Queue(maxsize=100)
                dir_queue = Queue()  # Queue for directories to create
                
                # Thread-safe counters
                progress_lock = threading.Lock()
                completed_count = [0]
                total_files = [0]  # Will be updated as we discover files
                scanning_done = [False]
                files_found = [False]  # Track if we found any files
                
                MAX_WORKERS = 10  # Fixed worker count like FileZilla
                
                def file_collector():
                    """Producer thread: walks directory and feeds files to queue"""
                    dir_list = set()
                    file_count = 0
                    
                    try:
                        for root, dirs, files in os.walk(local_save_path):
                            # Process directories
                            root_rel = os.path.relpath(root, local_save_path)
                            if root_rel == '.':
                                root_rel = ''
                            else:
                                root_rel = root_rel.replace('\\', '/')
                            
                            for dir_name in dirs:
                                if root_rel:
                                    remote_dir_path = f"{root_rel}/{dir_name}"
                                else:
                                    remote_dir_path = dir_name
                                if remote_dir_path not in dir_list:
                                    dir_list.add(remote_dir_path)
                                    dir_queue.put(remote_dir_path)
                            
                            # Process files - add to queue as we discover them
                            for filename in files:
                                file_count += 1
                                files_found[0] = True
                                local_file = os.path.join(root, filename)
                                if root_rel:
                                    remote_filename = f"{root_rel}/{filename}"
                                else:
                                    remote_filename = filename
                                
                                # Put file in queue (will block if queue is full, allowing workers to catch up)
                                file_queue.put((local_file, remote_filename))
                                with progress_lock:
                                    total_files[0] = file_count
                    
                    except Exception as e:
                        print(f"Error during file collection: {e}")
                    finally:
                        scanning_done[0] = True
                        # Wait for queue to empty before sending sentinels
                        # This ensures all discovered files are processed
                        file_queue.join()  # Wait for all items to be processed
                        # Put sentinel values to signal completion to all workers
                        for _ in range(MAX_WORKERS):
                            file_queue.put(None)
                
                # Start file collection in background thread
                collector_thread = threading.Thread(target=file_collector, daemon=True)
                collector_thread.start()
                
                # Create directories in background (non-blocking)
                def create_directories():
                    """Create directories as they're discovered"""
                    dirs_created = 0
                    while True:
                        try:
                            remote_dir_path = dir_queue.get(timeout=1)
                            try:
                                self.ftp_client.create_directory(
                                    username=username,
                                    game_name=game_name,
                                    folder_number=save_folder_number,
                                    remote_dir_path=remote_dir_path,
                                    ftp_path=ftp_path
                                )
                                dirs_created += 1
                            except Exception:
                                pass  # Directory might already exist
                            dir_queue.task_done()
                        except:
                            if scanning_done[0] and dir_queue.empty():
                                break
                
                dir_thread = threading.Thread(target=create_directories, daemon=True)
                dir_thread.start()
                
                def upload_worker():
                    """Worker function: pulls files from queue and uploads them continuously"""
                    worker_results = []
                    while True:
                        # Get file from queue
                        file_info = file_queue.get()
                        if file_info is None:  # Sentinel - no more files
                            file_queue.task_done()
                            break  # Exit loop when sentinel received
                        
                        local_file, remote_filename = file_info
                        try:
                            # Reuse connection within thread for better performance
                            success, message = self.ftp_client.upload_save(
                                username=username,
                                game_name=game_name,
                                local_file_path=local_file,
                                folder_number=save_folder_number,
                                remote_filename=remote_filename,
                                ftp_path=ftp_path
                            )
                            
                            # Update progress
                            with progress_lock:
                                completed_count[0] += 1
                                current = completed_count[0]
                                total = total_files[0]
                                # Show filename (truncate if too long)
                                display_name = remote_filename if len(remote_filename) <= 60 else remote_filename[:57] + "..."
                                if success:
                                    if total > 0:
                                        print(f"  [{current}/{total}] Uploaded: {display_name}")
                                        if operation_id:
                                            self._update_progress(operation_id, current, total, f"Uploaded: {display_name}")
                                    else:
                                        print(f"  [{current}] Uploaded: {display_name}")
                                        if operation_id:
                                            self._update_progress(operation_id, current, 0, f"Uploaded: {display_name}")
                                else:
                                    # Show error immediately - upload_save returned success=False
                                    error_msg = message if message else "Upload failed"
                                    if total > 0:
                                        print(f"  [{current}/{total}] FAILED: {display_name}")
                                        print(f"      Error: {error_msg}")
                                        if operation_id:
                                            self._update_progress(operation_id, current, total, f"Failed: {display_name}")
                                    else:
                                        print(f"  [{current}] FAILED: {display_name}")
                                        print(f"      Error: {error_msg}")
                                        if operation_id:
                                            self._update_progress(operation_id, current, 0, f"Failed: {display_name}")
                            
                            file_queue.task_done()
                            worker_results.append((success, remote_filename, message))
                        except Exception as e:
                            with progress_lock:
                                completed_count[0] += 1
                                current = completed_count[0]
                                total = total_files[0]
                                print(f"  [{current}/{total if total > 0 else '?'}] ERROR uploading {remote_filename}: {e}")
                                if operation_id:
                                    self._update_progress(operation_id, current, total if total > 0 else 0, f"Error: {remote_filename}")
                            file_queue.task_done()
                            worker_results.append((False, remote_filename, str(e)))
                    
                    return worker_results
                
                # Check if we found any files
                # Wait a moment for collector to start finding files
                time.sleep(0.1)
                if not files_found[0] and scanning_done[0]:
                    return {
                        'success': False,
                        'error': f'No files found in directory: {local_save_path}'
                    }
                
                print(f"Starting upload with {MAX_WORKERS} worker(s)...")
                
                # Process files in parallel - workers pull from queue as they become available
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    # Submit all workers
                    futures = [executor.submit(upload_worker) for _ in range(MAX_WORKERS)]
                    
                    # Process results as they complete
                    while futures:
                        done_futures = []
                        remaining_futures = []
                        
                        for future in futures:
                            if future.done():
                                done_futures.append(future)
                            else:
                                remaining_futures.append(future)
                        
                        for future in done_futures:
                            result = future.result()
                            # Worker returns a list of results (all files it processed)
                            if result:
                                for success, remote_filename, message in result:
                                    if success:
                                        uploaded_files.append(remote_filename)
                                    else:
                                        failed_files.append({'file': remote_filename, 'error': message})
                        
                        futures = remaining_futures
                        
                        # Small sleep to avoid busy waiting
                        if futures:
                            time.sleep(0.01)
                
                # Wait for threads to finish
                collector_thread.join(timeout=1)
                dir_thread.join(timeout=1)
                
                print(f"Upload complete: {len(uploaded_files)} succeeded, {len(failed_files)} failed")
                
                # Show failed files with error messages
                if failed_files:
                    print(f"\nFailed files ({len(failed_files)}):")
                    for i, failed in enumerate(failed_files[:20], 1):  # Show first 20 failures
                        file_name = failed.get('file', 'Unknown')
                        error_msg = failed.get('error', 'Unknown error')
                        display_name = file_name if len(file_name) <= 70 else file_name[:67] + "..."
                        print(f"  {i}. {display_name}")
                        print(f"     Error: {error_msg}")
                    if len(failed_files) > 20:
                        print(f"  ... and {len(failed_files) - 20} more failed files")
                
                # Note: Thread-local connections are automatically cleaned up when threads end
                
                if failed_files:
                    return {
                        'success': False,
                        'message': f'Uploaded {len(uploaded_files)} file(s), {len(failed_files)} failed',
                        'uploaded_files': uploaded_files,
                        'failed_files': failed_files
                    }
                
                return {
                    'success': True,
                    'message': f'Successfully uploaded {len(uploaded_files)} file(s)',
                    'uploaded_files': uploaded_files
                }
            else:
                # Single file upload
                print(f"Uploading single file: {os.path.basename(local_save_path)}")
                success, message = self.ftp_client.upload_save(
                    username=username,
                    game_name=game_name,
                    local_file_path=local_save_path,
                    folder_number=save_folder_number,
                    ftp_path=ftp_path
                )
                
                if success:
                    print(f"Upload complete: {os.path.basename(local_save_path)}")
                    return {'success': True, 'message': message}
                else:
                    print(f"Upload failed: {message}")
                    return {'success': False, 'error': message}
                    
        except Exception as e:
            print(f"Error: Save operation failed - {str(e)}")
            return {'success': False, 'error': f'Save operation failed: {str(e)}'}
    
    def load_game(self, game_id: int, local_save_path: str,
                 username: str, game_name: str, save_folder_number: int, ftp_path: Optional[str] = None,
                 operation_id: Optional[int] = None) -> Dict[str, Any]:
        """Load game - download from FTP to local PC"""
        print(f"Preparing to download save files...")
        
        try:
            success, files, directories, message = self.ftp_client.list_saves(
                username=username,
                game_name=game_name,
                folder_number=save_folder_number,
                ftp_path=ftp_path
            )
            
            if not success:
                return {
                    'success': False,
                    'error': f'Failed to list saves: {message}'
                }
            
            if not files and not directories:
                return {
                    'success': False,
                    'error': f'No save files or directories found: {message}'
                }
            
            downloaded_files = []
            failed_files = []
            
            # Ensure the local save path exists as a directory
            # Always treat it as a directory for loading (we download multiple files)
            # Handle case where path might be a file or directory
            if os.path.isfile(local_save_path):
                # If it's a file, use its parent directory instead
                local_save_path = os.path.dirname(local_save_path)
            
            # Create the directory and all parent directories if they don't exist
            try:
                os.makedirs(local_save_path, exist_ok=True)
            except OSError as e:
                print(f"Error: Failed to create directory - {str(e)}")
                return {
                    'success': False,
                    'error': f'Failed to create directory: {local_save_path} - {str(e)}'
                }
            
            # Verify it's actually a directory
            if not os.path.isdir(local_save_path):
                return {
                    'success': False,
                    'error': f'Local save path is not a directory: {local_save_path}'
                }
            
            # Create all directories first (including empty ones)
            if directories:
                for remote_dir_path in sorted(directories):  # Sort to create parent dirs first
                    # Normalize path separators
                    remote_dir_normalized = remote_dir_path.replace('\\', '/')
                    # Create local directory structure
                    local_dir = os.path.join(local_save_path, *remote_dir_normalized.split('/'))
                    os.makedirs(local_dir, exist_ok=True)
            
            # Streaming approach: download files on-demand as workers become available
            # Like FileZilla - starts downloading immediately, processes files as workers finish
            print("Starting download (processing files on-demand)...")
            
            # Queue for files to be downloaded (buffer up to 100 files ahead)
            file_queue = Queue(maxsize=100)
            
            # Thread-safe counters
            progress_lock = threading.Lock()
            completed_count = [0]
            total_files = [len(files)]
            processing_done = [False]
            
            MAX_WORKERS = 10  # Fixed worker count like FileZilla
            
            # Send initial progress
            if operation_id and total_files[0] > 0:
                self._update_progress(operation_id, 0, total_files[0], f"Found {total_files[0]} file(s) to download")
            
            def file_processor():
                """Producer: prepares files and feeds them to queue"""
                try:
                    for file_info in files:
                        remote_filename = file_info['name']
                        
                        # Normalize path separators to use forward slashes
                        remote_filename_normalized = remote_filename.replace('\\', '/')
                        # Build local file path using OS-specific separators
                        local_file = os.path.join(local_save_path, *remote_filename_normalized.split('/'))
                        
                        # Ensure parent directory exists (should already exist from above, but just in case)
                        local_dir = os.path.dirname(local_file)
                        if local_dir != local_save_path:
                            os.makedirs(local_dir, exist_ok=True)
                        
                        # Put file in queue (will block if queue is full, allowing workers to catch up)
                        file_queue.put((remote_filename, local_file))
                except Exception as e:
                    print(f"Error during file processing: {e}")
                finally:
                    processing_done[0] = True
                    # Wait for queue to empty before sending sentinels
                    file_queue.join()
                    # Put sentinel values to signal completion to all workers
                    for _ in range(MAX_WORKERS):
                        file_queue.put(None)
            
            # Start file processing in background thread
            processor_thread = threading.Thread(target=file_processor, daemon=True)
            processor_thread.start()
            
            def download_worker():
                """Worker function: pulls files from queue and downloads them continuously"""
                worker_results = []
                while True:
                    # Get file from queue
                    file_info = file_queue.get()
                    if file_info is None:  # Sentinel - no more files
                        file_queue.task_done()
                        break  # Exit loop when sentinel received
                    
                    remote_filename, local_file = file_info
                    try:
                        # Reuse connection within thread for better performance
                        success, message = self.ftp_client.download_save(
                            username=username,
                            game_name=game_name,
                            remote_filename=remote_filename,
                            local_file_path=local_file,
                            folder_number=save_folder_number,
                            ftp_path=ftp_path
                        )
                        
                        # Update progress
                        with progress_lock:
                            completed_count[0] += 1
                            current = completed_count[0]
                            total = total_files[0]
                            # Show filename (truncate if too long)
                            display_name = remote_filename if len(remote_filename) <= 60 else remote_filename[:57] + "..."
                            if success:
                                if total > 0:
                                    print(f"  [{current}/{total}] Downloaded: {display_name}")
                                    if operation_id:
                                        self._update_progress(operation_id, current, total, f"Downloaded: {display_name}")
                                else:
                                    print(f"  [{current}] Downloaded: {display_name}")
                                    if operation_id:
                                        self._update_progress(operation_id, current, 0, f"Downloaded: {display_name}")
                            else:
                                # Show error immediately
                                error_msg = message if message else "Download failed"
                                if total > 0:
                                    print(f"  [{current}/{total}] FAILED: {display_name}")
                                    print(f"      Error: {error_msg}")
                                    if operation_id:
                                        self._update_progress(operation_id, current, total, f"Failed: {display_name}")
                                else:
                                    print(f"  [{current}] FAILED: {display_name}")
                                    print(f"      Error: {error_msg}")
                                    if operation_id:
                                        self._update_progress(operation_id, current, 0, f"Failed: {display_name}")
                        
                        file_queue.task_done()
                        worker_results.append((success, remote_filename, message))
                    except Exception as e:
                        with progress_lock:
                            completed_count[0] += 1
                            current = completed_count[0]
                            total = total_files[0]
                            print(f"  [{current}/{total if total > 0 else '?'}] ERROR downloading {remote_filename}: {e}")
                            if operation_id:
                                self._update_progress(operation_id, current, total if total > 0 else 0, f"Error: {remote_filename}")
                        file_queue.task_done()
                        worker_results.append((False, remote_filename, str(e)))
                
                return worker_results
            
            # Wait a moment for processor to start
            time.sleep(0.1)
            
            print(f"Starting download with {MAX_WORKERS} worker(s)...")
            
            # Process files in parallel - workers pull from queue as they become available
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                # Submit all workers
                futures = [executor.submit(download_worker) for _ in range(MAX_WORKERS)]
                
                # Process results as they complete
                while futures:
                    done_futures = []
                    remaining_futures = []
                    
                    for future in futures:
                        if future.done():
                            done_futures.append(future)
                        else:
                            remaining_futures.append(future)
                    
                    for future in done_futures:
                        result = future.result()
                        # Worker returns a list of results (all files it processed)
                        if result:
                            for success, remote_filename, message in result:
                                if success:
                                    downloaded_files.append(remote_filename)
                                else:
                                    failed_files.append({'file': remote_filename, 'error': message})
                    
                    futures = remaining_futures
                    
                    # Small sleep to avoid busy waiting
                    if futures:
                        time.sleep(0.01)
            
            # Wait for threads to finish
            processor_thread.join(timeout=1)
            
            print(f"Download complete: {len(downloaded_files)} succeeded, {len(failed_files)} failed")
            
            # Show failed files with error messages
            if failed_files:
                print(f"\nFailed files ({len(failed_files)}):")
                for i, failed in enumerate(failed_files[:20], 1):  # Show first 20 failures
                    file_name = failed.get('file', 'Unknown')
                    error_msg = failed.get('error', 'Unknown error')
                    display_name = file_name if len(file_name) <= 70 else file_name[:67] + "..."
                    print(f"  {i}. {display_name}")
                    print(f"     Error: {error_msg}")
                if len(failed_files) > 20:
                    print(f"  ... and {len(failed_files) - 20} more failed files")
            
            if failed_files:
                return {
                    'success': False,
                    'message': f'Downloaded {len(downloaded_files)} file(s), {len(failed_files)} failed',
                    'downloaded_files': downloaded_files,
                    'failed_files': failed_files
                }
            
            return {
                'success': True,
                'message': f'Successfully downloaded {len(downloaded_files)} file(s)',
                'downloaded_files': downloaded_files
            }
                    
        except Exception as e:
            print(f"Error: Load operation failed - {str(e)}")
            return {'success': False, 'error': f'Load operation failed: {str(e)}'}
    
    def list_saves(self, game_id: int, username: str, game_name: str, 
                  save_folder_number: int, ftp_path: Optional[str] = None) -> Dict[str, Any]:
        """List all save files in a save folder"""
        print(f"Listing save files...")
        
        try:
            success, files, directories, message = self.ftp_client.list_saves(
                username=username,
                game_name=game_name,
                folder_number=save_folder_number,
                ftp_path=ftp_path
            )
            
            if not success:
                return {
                    'success': False,
                    'error': f'Failed to list saves: {message}'
                }
            
            print(f"Found {len(files)} file(s) and {len(directories)} directory(ies)")
            return {
                'success': True,
                'files': files,
                'directories': directories,
                'message': message
            }
        except Exception as e:
            print(f"ERROR: List operation failed: {e}")
            return {'success': False, 'error': f'List operation failed: {str(e)}'}
    
    def delete_save_folder(self, game_id: int, username: str, game_name: str,
                          save_folder_number: int, ftp_path: Optional[str] = None,
                          operation_id: Optional[int] = None) -> Dict[str, Any]:
        """Delete a save folder from FTP - FORCE DELETE (always deletes everything)"""
        print(f"Deleting save folder (force delete - will delete all contents)...")
        
        if not ftp_path:
            return {
                'success': False,
                'error': 'FTP path is required for delete operation'
            }
        
        try:
            # First, list all items to delete
            success, files, directories, message = self.ftp_client.list_saves(
                username=username,
                game_name=game_name,
                folder_number=save_folder_number,
                ftp_path=ftp_path
            )
            
            if not success:
                return {
                    'success': False,
                    'error': f'Failed to list items for deletion: {message}'
                }
            
            # Collect all items to delete (files first, then directories)
            items_to_delete = []
            
            # Add all files
            for file_info in files:
                items_to_delete.append({
                    'type': 'file',
                    'path': file_info['name'],
                    'full_path': None  # Will be constructed during deletion
                })
            
            # Add all directories (sorted by depth, deepest first)
            # This ensures we delete child directories before parent directories
            dir_paths = sorted(directories, key=lambda x: x.count('/'), reverse=True)
            for dir_path in dir_paths:
                items_to_delete.append({
                    'type': 'directory',
                    'path': dir_path,
                    'full_path': None
                })
            
            # Add the root directory itself (last)
            items_to_delete.append({
                'type': 'directory',
                'path': '',
                'full_path': ftp_path
            })
            
            if not items_to_delete:
                # Nothing to delete
                return {
                    'success': True,
                    'message': 'Save folder is already empty'
                }
            
            # Streaming approach: delete items on-demand as workers become available
            print("Starting delete (processing items on-demand)...")
            
            # Queue for items to be deleted (buffer up to 100 items ahead)
            delete_queue = Queue(maxsize=100)
            
            # Thread-safe counters
            progress_lock = threading.Lock()
            completed_count = [0]
            total_items = [len(items_to_delete)]
            processing_done = [False]
            
            MAX_WORKERS = 10  # Fixed worker count like FileZilla
            
            # Send initial progress
            if operation_id and total_items[0] > 0:
                self._update_progress(operation_id, 0, total_items[0], f"Found {total_items[0]} item(s) to delete")
            
            def item_processor():
                """Producer: prepares items and feeds them to queue"""
                try:
                    for item in items_to_delete:
                        # Put item in queue (will block if queue is full, allowing workers to catch up)
                        delete_queue.put(item)
                except Exception as e:
                    print(f"Error during item processing: {e}")
                finally:
                    processing_done[0] = True
                    # Wait for queue to empty before sending sentinels
                    delete_queue.join()
                    # Put sentinel values to signal completion to all workers
                    for _ in range(MAX_WORKERS):
                        delete_queue.put(None)
            
            # Start item processing in background thread
            processor_thread = threading.Thread(target=item_processor, daemon=True)
            processor_thread.start()
            
            deleted_items = []
            failed_items = []
            
            def delete_worker():
                """Worker function: pulls items from queue and deletes them continuously"""
                worker_results = []
                while True:
                    # Get item from queue
                    item = delete_queue.get()
                    if item is None:  # Sentinel - no more items
                        delete_queue.task_done()
                        break  # Exit loop when sentinel received
                    
                    item_type = item['type']
                    item_path = item['path']
                    
                    try:
                        # Build full path
                        if item['full_path']:
                            full_path = item['full_path']
                        else:
                            # Construct full path from base ftp_path
                            if item_path:
                                full_path = f"{ftp_path.rstrip('/')}/{item_path.lstrip('/')}"
                            else:
                                full_path = ftp_path
                        
                        # Delete the item
                        if item_type == 'file':
                            # Delete file using delete_file helper
                            success, message = self.ftp_client.delete_file(full_path)
                        else:
                            # Delete directory using delete_directory helper
                            # Since we're deleting in order (deepest first), directories should be empty
                            success, message = self.ftp_client.delete_directory(full_path)
                        
                        # Update progress
                        with progress_lock:
                            completed_count[0] += 1
                            current = completed_count[0]
                            total = total_items[0]
                            # Show item name (truncate if too long)
                            display_name = item_path if item_path and len(item_path) <= 60 else (item_path[:57] + "..." if item_path else os.path.basename(full_path))
                            if success:
                                if total > 0:
                                    print(f"  [{current}/{total}] Deleted: {display_name}")
                                    if operation_id:
                                        self._update_progress(operation_id, current, total, f"Deleted: {display_name}")
                                else:
                                    print(f"  [{current}] Deleted: {display_name}")
                                    if operation_id:
                                        self._update_progress(operation_id, current, 0, f"Deleted: {display_name}")
                            else:
                                # Show error immediately
                                error_msg = message if message else "Delete failed"
                                if total > 0:
                                    print(f"  [{current}/{total}] FAILED: {display_name}")
                                    print(f"      Error: {error_msg}")
                                    if operation_id:
                                        self._update_progress(operation_id, current, total, f"Failed: {display_name}")
                                else:
                                    print(f"  [{current}] FAILED: {display_name}")
                                    print(f"      Error: {error_msg}")
                                    if operation_id:
                                        self._update_progress(operation_id, current, 0, f"Failed: {display_name}")
                        
                        delete_queue.task_done()
                        worker_results.append((success, item_path, message))
                    except Exception as e:
                        with progress_lock:
                            completed_count[0] += 1
                            current = completed_count[0]
                            total = total_items[0]
                            display_name = item_path if item_path and len(item_path) <= 60 else (item_path[:57] + "..." if item_path else "unknown")
                            print(f"  [{current}/{total if total > 0 else '?'}] ERROR deleting {display_name}: {e}")
                            if operation_id:
                                self._update_progress(operation_id, current, total if total > 0 else 0, f"Error: {display_name}")
                        delete_queue.task_done()
                        worker_results.append((False, item_path, str(e)))
                
                return worker_results
            
            # Wait a moment for processor to start
            time.sleep(0.1)
            
            print(f"Starting delete with {MAX_WORKERS} worker(s)...")
            
            # Process items in parallel - workers pull from queue as they become available
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                # Submit all workers
                futures = [executor.submit(delete_worker) for _ in range(MAX_WORKERS)]
                
                # Process results as they complete
                while futures:
                    done_futures = []
                    remaining_futures = []
                    
                    for future in futures:
                        if future.done():
                            done_futures.append(future)
                        else:
                            remaining_futures.append(future)
                    
                    for future in done_futures:
                        result = future.result()
                        # Worker returns a list of results (all items it processed)
                        if result:
                            for success, item_path, message in result:
                                if success:
                                    deleted_items.append(item_path)
                                else:
                                    failed_items.append({'item': item_path, 'error': message})
                    
                    futures = remaining_futures
                    
                    # Small sleep to avoid busy waiting
                    if futures:
                        time.sleep(0.01)
            
            # Wait for threads to finish
            processor_thread.join(timeout=1)
            
            print(f"Delete complete: {len(deleted_items)} succeeded, {len(failed_items)} failed")
            
            # Show failed items with error messages
            if failed_items:
                print(f"\nFailed items ({len(failed_items)}):")
                for i, failed in enumerate(failed_items[:20], 1):  # Show first 20 failures
                    item_name = failed.get('item', 'Unknown')
                    error_msg = failed.get('error', 'Unknown error')
                    display_name = item_name if len(item_name) <= 70 else item_name[:67] + "..."
                    print(f"  {i}. {display_name}")
                    print(f"     Error: {error_msg}")
                if len(failed_items) > 20:
                    print(f"  ... and {len(failed_items) - 20} more failed items")
            
            if failed_items:
                return {
                    'success': False,
                    'message': f'Deleted {len(deleted_items)} item(s), {len(failed_items)} failed',
                    'deleted_items': deleted_items,
                    'failed_items': failed_items
                }
            
            return {
                'success': True,
                'message': f'Successfully deleted {len(deleted_items)} item(s)',
                'deleted_items': deleted_items
            }
                    
        except Exception as e:
            print(f"Error: Delete operation failed - {str(e)}")
            return {'success': False, 'error': f'Delete operation failed: {str(e)}'}
    
    def register_with_server(self, client_id: str) -> bool:
        """Register this client with the Django server"""
        try:
            response = self.session.post(
                f"{self.server_url}/api/client/register/",
                json={'client_id': client_id}
            )
            if response.status_code == 200:
                return True
            else:
                print(f"Error: Registration failed - {response.status_code}")
                return False
        except Exception as e:
            print(f"Error: Failed to register with server - {str(e)}")
            return False
    
    def send_heartbeat(self, client_id: str) -> bool:
        """Send heartbeat to Django server"""
        try:
            response = self.session.post(
                f"{self.server_url}/api/client/heartbeat/",
                json={'client_id': client_id},
                timeout=5  # Short timeout for heartbeat
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def _heartbeat_loop(self, client_id: str):
        """Background thread that continuously sends heartbeats"""
        heartbeat_interval = 10  # Send heartbeat every 10 seconds (server timeout is 30 seconds)
        while self.running:
            try:
                self.send_heartbeat(client_id)
            except Exception:
                pass  # Silently fail - will retry on next interval
            # Sleep in small increments so we can check self.running frequently
            for _ in range(heartbeat_interval * 10):  # 10 seconds = 100 * 0.1 second sleeps
                if not self.running:
                    break
                time.sleep(0.1)
    
    def unregister_from_server(self, client_id: str) -> bool:
        """Unregister this client from the Django server (called on shutdown)"""
        try:
            response = self.session.post(
                f"{self.server_url}/api/client/unregister/",
                json={'client_id': client_id}
            )
            return response.status_code == 200
        except Exception:
            return False
            return False
    
    def run(self):
        """Run the service (polling mode)"""
        print("Starting Client Worker Service...")
        
        # Check permissions
        if not self.check_permissions():
            print("Warning: Insufficient permissions - you may need elevated privileges")
        
        self.running = True
        
        # Generate unique client ID based on PC information
        # This ensures each PC has a unique identifier
        import platform
        import uuid
        
        # Try to get a unique identifier for this PC
        # Use MAC address + hostname for uniqueness
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                           for elements in range(0,2*6,2)][::-1])
            hostname = platform.node() or platform.uname().node
            client_id = f"{hostname}_{mac}"
        except:
            # Fallback to hostname + machine ID if MAC address unavailable
            hostname = platform.node() or platform.uname().node or 'unknown'
            try:
                # Try to get machine ID (Linux) or use hostname + system info
                if sys.platform == 'linux':
                    import subprocess
                    machine_id = subprocess.check_output(['cat', '/etc/machine-id']).decode().strip()[:8]
                    client_id = f"{hostname}_{machine_id}"
                else:
                    # Windows/Mac fallback
                    machine_info = platform.machine() + platform.processor()
                    client_id = f"{hostname}_{hash(machine_info) & 0xffffffff:08x}"
            except:
                # Last resort: hostname + random UUID (stored for persistence)
                # Store in a file so it's consistent across runs
                client_id_file = Path.home() / '.savenload' / 'client_id.txt'
                if client_id_file.exists():
                    client_id = client_id_file.read_text().strip()
                else:
                    client_id = f"{hostname}_{uuid.uuid4().hex[:8]}"
                    client_id_file.parent.mkdir(parents=True, exist_ok=True)
                    client_id_file.write_text(client_id)
        
        # Register with server
        if not self.register_with_server(client_id):
            print("Error: Failed to register with server. Exiting.")
            return
        
        # Store client_id
        self._current_client_id = client_id
        
        print(f"Connected to server")
        print(f"Service running (checking for operations every {self.poll_interval} second(s))...")
        
        # Start heartbeat thread (runs continuously, even during long operations)
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, args=(client_id,), daemon=True)
        self._heartbeat_thread.start()
        print("Heartbeat thread started (sending heartbeats every 10 seconds)")
        
        # Open server URL in default browser
        browser_opened = False
        try:
            webbrowser.open(self.server_url)
            browser_opened = True
        except Exception:
            pass
        
        # Show URL if browser didn't open or as backup
        if not browser_opened:
            print(f"\nServer URL: {self.server_url}")
            print("(Copy the URL above to open in your browser)")
        else:
            print(f"\nServer URL: {self.server_url}")
        
        try:
            while self.running:
                # Poll server for pending operations
                # Note: Heartbeat is sent in separate thread, so it continues during long operations
                try:
                    response = self.session.get(
                        f"{self.server_url}/api/client/pending/{client_id}/",
                        timeout=5  # Short timeout for polling
                    )
                    if response.status_code == 200:
                        data = response.json()
                        operations = data.get('operations', [])
                        for op in operations:
                            self._process_operation(op)
                except Exception:
                    pass
                
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.running = False
        finally:
            # Wait for heartbeat thread to finish
            if self._heartbeat_thread and self._heartbeat_thread.is_alive():
                # Thread will exit when self.running becomes False
                self._heartbeat_thread.join(timeout=2)
            # Unregister on shutdown
            try:
                self.unregister_from_server(client_id)
            except Exception:
                pass
    
    def _process_operation(self, operation: Dict[str, Any]):
        """Process a pending operation from the server"""
        op_type = operation.get('type')
        operation_id = operation.get('id')
        game_id = operation.get('game_id')
        local_path = operation.get('local_save_path')
        username = operation.get('username')
        game_name = operation.get('game_name')
        save_folder_number = operation.get('save_folder_number')
        ftp_path = operation.get('ftp_path')
        
        op_type_display = op_type.capitalize()
        print(f"\nProcessing: {op_type_display} operation for {game_name}")
        
        # save_folder_number is required for save/load/list/delete operations
        if op_type in ['save', 'load', 'list', 'delete'] and save_folder_number is None:
            print(f"Error: Operation missing required information")
            return
        
        if op_type == 'save':
            result = self.save_game(game_id, local_path, username, game_name, save_folder_number, ftp_path, operation_id)
        elif op_type == 'load':
            result = self.load_game(game_id, local_path, username, game_name, save_folder_number, ftp_path, operation_id)
        elif op_type == 'list':
            result = self.list_saves(game_id, username, game_name, save_folder_number, ftp_path)
        elif op_type == 'delete':
            result = self.delete_save_folder(game_id, username, game_name, save_folder_number, ftp_path, operation_id)
        else:
            print(f"Error: Unknown operation type")
            return
        
        # Log the result
        if result.get('success'):
            message = result.get('message', 'Operation completed successfully')
            print(f"Success: {message}")
        else:
            error = result.get('error', result.get('message', 'Unknown error'))
            print(f"Error: {error}")
        
        # Report result back to server
        try:
            self.session.post(
                f"{self.server_url}/api/client/complete/{operation_id}/",
                json=result
            )
        except Exception:
            pass
    

def main():
    """Main entry point"""
    import argparse
    
    # Check for server URL in environment variable first
    server_url = os.getenv('SAVENLOAD_SERVER_URL', '').strip()
    
    parser = argparse.ArgumentParser(description='SaveNLoad Client Worker Service')
    parser.add_argument('--server', default=server_url, 
                       help='Django server URL (defaults to SAVENLOAD_SERVER_URL env var)')
    parser.add_argument('--poll-interval', type=int, default=5, help='Poll interval in seconds')
    
    args = parser.parse_args()
    
    if not args.server:
        print("Error: Server URL is required. Set SAVENLOAD_SERVER_URL environment variable or use --server argument.")
        parser.print_help()
        sys.exit(1)
    
    try:
        service = ClientWorkerService(args.server, args.poll_interval)
        service.run()
    except Exception as e:
        print(f"Error: Service failed - {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()

