"""
API endpoints for client worker registration and communication
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from SaveNLoad.models import SimpleUsers, Game
from SaveNLoad.services.redis_worker_service import (
    register_worker,
    ping_worker,
    get_worker_info,
    claim_worker as redis_claim_worker,
    unclaim_worker as redis_unclaim_worker,
    get_user_workers,
    is_worker_online,
    get_unclaimed_workers
)
from SaveNLoad.services.redis_operation_service import (
    get_pending_operations as redis_get_pending_operations,
    update_operation_progress as redis_update_operation_progress,
    complete_operation as redis_complete_operation,
    fail_operation as redis_fail_operation,
    get_operation,
    get_operations_by_game,
    get_operations_by_user
)
from SaveNLoad.views.api_helpers import (
    parse_json_body,
    json_response_error,
    json_response_success,
    delete_game_banner_file
)
import json
import os


@csrf_exempt
@require_http_methods(["POST"])
def register_client(request):
    """Register a client worker - client_id must be unique per PC"""
    try:
        data, error_response = parse_json_body(request)
        if error_response:
            return error_response
        
        client_id = data.get('client_id', '').strip()
        
        if not client_id:
            return json_response_error('client_id is required', status=400)
        
        # Get existing worker info to check for linked user
        worker_info = get_worker_info(client_id)
        user_id = worker_info['user_id'] if worker_info and worker_info.get('user_id') else None
        
        # Auto-claim to currently logged-in user if not already claimed
        if not user_id:
            from SaveNLoad.views.custom_decorators import get_current_user
            current_user = get_current_user(request)
            if current_user:
                user_id = current_user.id
                print(f"Auto-claiming worker {client_id} to logged-in user: {current_user.username}")
        
        # Register worker (creates or updates)
        register_worker(client_id, user_id)
        
        # Get linked user username if exists
        linked_user = None
        if user_id:
            try:
                user = SimpleUsers.objects.get(pk=user_id)
                linked_user = user.username
            except SimpleUsers.DoesNotExist:
                pass
        
        print(f"Client worker registered: {client_id}")
        return json_response_success(
            message='Client worker registered successfully',
            data={
                'client_id': client_id,
                'linked_user': linked_user
            }
        )
        
    except Exception as e:
        print(f"ERROR: Failed to register client: {e}")
        return json_response_error(str(e), status=500)


@csrf_exempt
@require_http_methods(["GET"])
def ping_worker(request, client_id):
    """Ping endpoint for workers to confirm they're alive - refreshes Redis TTL"""
    try:
        # Check if worker exists, if not register it
        if not is_worker_online(client_id):
            register_worker(client_id)
        
        # Update heartbeat
        from SaveNLoad.services.redis_worker_service import ping_worker as redis_ping_worker
        result = redis_ping_worker(client_id)
        
        return json_response_success(data=result)
        
    except Exception as e:
        print(f"ERROR: Failed to process ping: {e}")
        return json_response_error(str(e), status=500)


@csrf_exempt
@require_http_methods(["POST"])
def unregister_client(request):
    """Unregister a client worker (called on shutdown)"""
    try:
        data, error_response = parse_json_body(request)
        if error_response:
            return error_response
        
        client_id = data.get('client_id', '').strip()
        
        # With Redis TTL, worker will automatically become offline when heartbeat expires
        # No explicit cleanup needed
        print(f"Client worker unregistered: {client_id}")
        return json_response_success(message='Client worker unregistered')
        
    except Exception as e:
        print(f"ERROR: Failed to unregister client: {e}")
        return json_response_error(str(e), status=500)


@csrf_exempt
@require_http_methods(["GET"])
def check_connection(request):
    """Check if client worker is connected for current user"""
    from SaveNLoad.views.custom_decorators import get_current_user
    
    user = get_current_user(request)
    if not user:
        return JsonResponse({
            'connected': False,
            'client_id': None,
            'last_ping_response': None,
        })
    
    # Get online workers for this user
    worker_ids = get_user_workers(user.id)
    
    if not worker_ids:
        return JsonResponse({
            'connected': False,
            'client_id': None,
            'last_ping_response': None,
            'message': 'No active devices found. Please ensure your client is running.'
        })
    
    # Get most recent worker (first one, as they're already filtered to online)
    client_id = worker_ids[0]
    worker_info = get_worker_info(client_id)
    
    return JsonResponse({
        'connected': True,
        'client_id': client_id,
        'last_ping_response': worker_info['last_ping'] if worker_info else None,
        'worker_count': len(worker_ids)
    })


@csrf_exempt
@require_http_methods(["GET"])
def get_pending_operations(request, client_id):
    """Get pending operations for a client worker"""
    try:
        # Check if worker exists
        if not is_worker_online(client_id):
            return json_response_error('Client worker not found or offline', status=404)
        
        # Get pending operations (automatically marks them as in_progress)
        operations_list = redis_get_pending_operations(client_id)
        
        # Get linked user
        worker_info = get_worker_info(client_id)
        linked_user = None
        if worker_info and worker_info.get('user_id'):
            try:
                user = SimpleUsers.objects.get(pk=worker_info['user_id'])
                linked_user = user.username
            except SimpleUsers.DoesNotExist:
                pass
        
        return JsonResponse({
            'operations': operations_list,
            'linked_user': linked_user
        })
        
    except Exception as e:
        print(f"ERROR: Failed to get pending operations: {e}")
        return json_response_error(str(e), status=500)


@csrf_exempt
@require_http_methods(["POST"])
def update_operation_progress(request, operation_id):
    """Update progress for an operation"""
    try:
        data = json.loads(request.body or "{}")
        
        # Check if operation exists
        operation = get_operation(operation_id)
        if not operation:
            return json_response_error('Operation not found', status=404)
        
        # Update progress
        current = data.get('current')
        total = data.get('total')
        message = data.get('message')
        
        redis_update_operation_progress(operation_id, current, total, message)
        
        return json_response_success()
        
    except Exception as e:
        print(f"ERROR: Failed to update operation progress: {e}")
        return json_response_error(str(e), status=500)



def _check_and_handle_game_deletion_completion(operation_dict, game):
    """
    Check if game deletion is pending and all operations are complete.
    If so, either delete the game (if all succeeded) or cancel deletion (if any failed).
    
    Args:
        operation_dict: Operation dict from Redis
        game: Game model instance
    """
    from SaveNLoad.utils.operation_utils import is_game_deletion_operation
    
    # Check if this is a game deletion operation
    if not (game and game.pending_deletion and 
            operation_dict.get('type') == 'delete' and 
            not operation_dict.get('save_folder_number')):
        return

    # Get all operations for this game
    all_operations = get_operations_by_game(game.id)
    
    # Filter to only delete operations without save_folder_number
    game_deletion_ops = [op for op in all_operations 
                        if op.get('type') == 'delete' and not op.get('save_folder_number')]
    
    # Check if any are still pending or in progress (excluding current)
    remaining = [op for op in game_deletion_ops 
                if op.get('id') != operation_dict.get('id') and 
                op.get('status') in ['pending', 'in_progress']]
    
    if remaining:
        return

    # All operations are complete - check if all succeeded
    failed_ops = [op for op in game_deletion_ops if op.get('status') == 'failed']
    all_succeeded = len(failed_ops) == 0
    
    if all_succeeded:
        # All operations succeeded - delete the game
        game_name = game.name
        game_id = game.id
        
        # Delete banner file before deleting game
        delete_game_banner_file(game)
        
        game.delete()
        print(f"Game {game_id} ({game_name}) deleted from database after all storage cleanup operations completed successfully")
    else:
        # Some operations failed - keep the game, clear pending_deletion flag
        game.pending_deletion = False
        game.save()
        print(f"WARNING: Game {game.id} ({game.name}) deletion cancelled - {len(failed_ops)} storage operation(s) failed")


def _check_and_handle_user_deletion_completion(operation_dict, user):
    """
    Check if user deletion is pending and all operations are complete.
    If so, either delete the user (if all succeeded) or cancel deletion (if any failed).
    
    Args:
        operation_dict: Operation dict from Redis
        user: User model instance
    """
    # Check if this is a user deletion operation
    if not (user and hasattr(user, 'pending_deletion') and user.pending_deletion and
            operation_dict.get('type') == 'delete' and 
            not operation_dict.get('game_id') and
            not operation_dict.get('save_folder_number')):
        return

    print(f"DEBUG: Checking user deletion completion for user {user.id} ({user.username})")
    
    # Get all user deletion operations for this user
    # User deletion operations have game_id=None
    all_operations = get_operations_by_user(
        user.id, 
        game_id=None, 
        operation_type='delete'
    )
    
    # Filter to only those without save_folder_number
    user_deletion_ops = [op for op in all_operations if not op.get('save_folder_number')]
    
    print(f"DEBUG: Found {len(user_deletion_ops)} user deletion operations for user {user.id}")
    
    # Check if all operations are complete (excluding current)
    remaining = [op for op in user_deletion_ops 
                if op.get('id') != operation_dict.get('id') and 
                op.get('status') in ['pending', 'in_progress']]
    
    if remaining:
        print(f"DEBUG: Still {len(remaining)} pending/in-progress operations for user {user.id}")
        return

    # All operations are complete - check if all succeeded
    failed_ops = [op for op in user_deletion_ops if op.get('status') == 'failed']
    completed_ops = [op for op in user_deletion_ops if op.get('status') == 'completed']
    total_ops = len(user_deletion_ops)
    
    all_succeeded = (len(failed_ops) == 0) and (len(completed_ops) == total_ops) and (total_ops > 0)
    
    print(f"DEBUG: User deletion operations - Total: {total_ops}, Completed: {len(completed_ops)}, Failed: {len(failed_ops)}, All succeeded: {all_succeeded}")
    
    if all_succeeded:
        # All operations succeeded - delete the user
        username = user.username
        user_id = user.id
        
        # Add a small delay before deleting to give frontend time to poll operation status
        import time
        time.sleep(3)
        
        user.delete()
        print(f"User {user_id} ({username}) deleted from database after storage cleanup operation completed successfully")
    else:
        # Some operations failed - keep the user, clear pending_deletion flag
        user.pending_deletion = False
        user.save()
        print(f"WARNING: User {user.id} ({user.username}) deletion cancelled - {len(failed_ops)} storage operation(s) failed")


@csrf_exempt
@require_http_methods(["POST"])
def complete_operation(request, operation_id):
    """Mark an operation as complete"""
    from django.utils import timezone
    
    try:
        data = json.loads(request.body or "{}")
        
        # Get operation from Redis
        operation_dict = get_operation(operation_id)
        if not operation_dict:
            return json_response_error('Operation not found', status=404)
        
        # Get user and game from database
        user = None
        game = None
        if operation_dict.get('user_id'):
            try:
                user = SimpleUsers.objects.get(pk=operation_dict['user_id'])
            except SimpleUsers.DoesNotExist:
                pass
        
        if operation_dict.get('game_id'):
            try:
                game = Game.objects.get(pk=operation_dict['game_id'])
            except Game.DoesNotExist:
                pass
        
        success = data.get('success', False)
        if success:
            redis_complete_operation(operation_id, result_data=data)
            
            # Update game's last_played when save operation completes successfully
            if operation_dict.get('type') == 'save' and game:
                game.last_played = timezone.now()
                game.save()
            
            # Delete save folder from database when DELETE operation completes successfully
            if (operation_dict.get('type') == 'delete' and 
                operation_dict.get('save_folder_number') and game):
                from SaveNLoad.models.save_folder import SaveFolder
                try:
                    save_folder = SaveFolder.get_by_number(
                        user,
                        game,
                        operation_dict['save_folder_number']
                    )
                    if save_folder:
                        save_folder.delete()
                        print(f"Deleted save folder {operation_dict['save_folder_number']} from database after successful SMB deletion")
                except Exception as e:
                    print(f"WARNING: Failed to delete save folder from database after operation: {e}")
            
            # Check if game is pending deletion and all operations are complete
            if game:
                _check_and_handle_game_deletion_completion(operation_dict, game)
            
            # Check if user is pending deletion and all operations are complete
            if user:
                _check_and_handle_user_deletion_completion(operation_dict, user)
        else:
            error_message = data.get('error', data.get('message', 'Operation failed'))
            
            # Transform error messages to be user-friendly
            from SaveNLoad.utils.string_utils import transform_path_error_message
            error_message = transform_path_error_message(error_message, operation_dict.get('type', ''))
            
            redis_fail_operation(operation_id, error_message)
            
            # Check if game is pending deletion and all operations are complete
            if game:
                _check_and_handle_game_deletion_completion(operation_dict, game)
            
            # Check if user is pending deletion and all operations are complete
            if user:
                _check_and_handle_user_deletion_completion(operation_dict, user)
            
            # Cleanup: If SAVE operation failed due to missing local path or empty saves, delete the save folder
            if (operation_dict.get('type') == 'save' and 
                operation_dict.get('save_folder_number') and user and game):
                error_lower = error_message.lower() if error_message else ''
                path_errors = [
                    'does not exist', 'not found', 'local save path', 'local file not found',
                    'local path does not exist', "don't have any save files", "haven't played the game",
                    'empty', 'is empty', 'no files', 'no files were transferred', 'no files to save',
                    '0 bytes', 'nothing to save', 'contains no valid files', 'appears to be empty'
                ]
                if any(err in error_lower for err in path_errors):
                    from SaveNLoad.models.save_folder import SaveFolder
                    try:
                        save_folder = SaveFolder.get_by_number(
                            user, 
                            game, 
                            operation_dict['save_folder_number']
                        )
                        if save_folder:
                            # Check if there are other operations for this save folder
                            other_ops = get_operations_by_user(
                                user.id, 
                                game_id=game.id, 
                                operation_type='save'
                            )
                            other_ops = [op for op in other_ops 
                                        if op.get('save_folder_number') == operation_dict.get('save_folder_number') and
                                        op.get('id') != operation_id]
                            
                            # Check if any are still pending/in-progress
                            pending = [op for op in other_ops if op.get('status') in ['pending', 'in_progress']]
                            
                            if not pending:
                                # Check if all others failed
                                all_failed = all(op.get('status') == 'failed' for op in other_ops)
                                if all_failed:
                                    save_folder.delete()
                                    print(f"Deleted save folder {save_folder.folder_number} due to failed save operation")
                    except Exception as e:
                        print(f"WARNING: Failed to cleanup save folder after failed operation: {e}")
        
        return json_response_success()
        
    except Exception as e:
        print(f"ERROR: Failed to complete operation: {e}")
        return json_response_error(str(e), status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_unpaired_workers(request):
    """Get list of all online workers with their claim status"""
    from SaveNLoad.views.custom_decorators import get_current_user
    from SaveNLoad.services.redis_worker_service import get_online_workers
    
    user = get_current_user(request)
    if not user:
        return json_response_error('Authentication required', status=401)
    
    # Get all online workers
    online_worker_ids = get_online_workers()
    
    workers_list = []
    for client_id in online_worker_ids:
        worker_info = get_worker_info(client_id)
        user_id = worker_info.get('user_id') if worker_info else None
        linked_username = None
        if user_id:
            try:
                linked_user = SimpleUsers.objects.get(pk=user_id)
                linked_username = linked_user.username
            except SimpleUsers.DoesNotExist:
                pass
        
        workers_list.append({
            'client_id': client_id,
            'last_ping_response': worker_info['last_ping'] if worker_info else None,
            'hostname': client_id,
            'linked_user': linked_username,
            'claimed': user_id is not None
        })
    
    return JsonResponse({
        'workers': workers_list
    })


@csrf_exempt
@require_http_methods(["POST"])
def claim_worker(request):
    """Claim a worker for the current user"""
    from SaveNLoad.views.custom_decorators import get_current_user
    
    try:
        user = get_current_user(request)
        if not user:
            return json_response_error('Authentication required', status=401)
            
        data, error_response = parse_json_body(request)
        if error_response:
            return error_response
            
        client_id = data.get('client_id', '').strip()
        if not client_id:
            return json_response_error('client_id is required', status=400)
            
        # Check if worker exists and is online
        if not is_worker_online(client_id):
            return json_response_error('Worker not found or offline', status=404)
        
        # Check if already claimed by another user
        worker_info = get_worker_info(client_id)
        if worker_info and worker_info.get('user_id') and worker_info['user_id'] != user.id:
            return json_response_error('Worker is already claimed by another user', status=409)
            
        # Claim it
        success = redis_claim_worker(client_id, user.id)
        if not success:
            return json_response_error('Failed to claim worker', status=500)
        
        print(f"Worker {client_id} claimed by {user.username}")
        return json_response_success(message='Worker claimed successfully')
        
    except Exception as e:
        print(f"ERROR: Failed to claim worker: {e}")
        return json_response_error(str(e), status=500)


@csrf_exempt
@require_http_methods(["POST"])
def unclaim_worker(request):
    """Unclaim a worker (release ownership)"""
    from SaveNLoad.views.custom_decorators import get_current_user
    
    try:
        user = get_current_user(request)
        if not user:
            return json_response_error('Authentication required', status=401)
            
        data, error_response = parse_json_body(request)
        if error_response:
            return error_response
            
        client_id = data.get('client_id', '').strip()
        if not client_id:
            return json_response_error('client_id is required', status=400)
        
        # Check if worker exists and is owned by this user
        worker_info = get_worker_info(client_id)
        if not worker_info:
            return json_response_error('Worker not found', status=404)
        
        if not worker_info.get('user_id') or worker_info['user_id'] != user.id:
            return json_response_error('Worker not found or not owned by you', status=404)
            
        # Release it
        redis_unclaim_worker(client_id)
        
        print(f"Worker {client_id} unclaimed by {user.username}")
        return json_response_success(message='Worker unclaimed successfully')
        
    except Exception as e:
        print(f"ERROR: Failed to unclaim worker: {e}")
        return json_response_error(str(e), status=500)



