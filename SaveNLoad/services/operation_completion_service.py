from django.utils import timezone
from SaveNLoad.services.redis_operation_service import (
    complete_operation as redis_complete_operation,
    fail_operation as redis_fail_operation,
    get_operation,
    get_operations_by_game,
    get_operations_by_user,
)
from SaveNLoad.utils.string_utils import transform_path_error_message
import os


def process_operation_completion(operation_id, payload):
    """
    Handle operation completion payloads from the worker.
    
    Args:
        operation_id: Operation identifier
        payload: Completion payload from worker
    
    Returns:
        tuple: (success_bool, error_message_or_none)
    """
    operation_dict = get_operation(operation_id)
    if not operation_dict:
        return False, 'Operation not found'

    # Load related DB objects only when needed.
    user = _get_user(operation_dict.get('user_id'))
    game = _get_game(operation_dict.get('game_id'))

    success = payload.get('success', False)
    if success:
        # Persist completion in Redis before touching DB side effects.
        redis_complete_operation(operation_id, result_data=payload)

        if operation_dict.get('type') == 'save' and game:
            # Update playtime timestamp on successful save.
            game.last_played = timezone.now()
            game.save()

        if (operation_dict.get('type') == 'delete' and
                operation_dict.get('save_folder_number') and game):
            # Cleanup corresponding SaveFolder entry.
            _delete_save_folder_after_delete(user, game, operation_dict)

        if game:
            # Game deletions require all related ops to complete.
            _check_and_handle_game_deletion_completion(operation_dict, game)

        if user:
            # User deletions require all related ops to complete.
            _check_and_handle_user_deletion_completion(operation_dict, user)

        return True, None

    # Failure path: normalize message for user display.
    error_message = payload.get('error', payload.get('message', 'Operation failed'))
    error_message = transform_path_error_message(error_message, operation_dict.get('type', ''))

    redis_fail_operation(operation_id, error_message)

    if game:
        # Still check for game deletion completion on failure.
        _check_and_handle_game_deletion_completion(operation_dict, game)

    if user:
        # Still check for user deletion completion on failure.
        _check_and_handle_user_deletion_completion(operation_dict, user)

    if (operation_dict.get('type') == 'save' and
            operation_dict.get('save_folder_number') and user and game):
        # If failure is due to missing/empty saves, cleanup DB record.
        _cleanup_failed_save_folder(operation_id, operation_dict, user, game, error_message)

    return False, error_message


def _get_user(user_id):
    """
    Resolve a SimpleUsers instance (lazy import avoids ASGI app registry issues).
    
    Args:
        user_id: User ID
    
    Returns:
        SimpleUsers instance or None
    """
    if not user_id:
        return None
    # Import inside function to avoid app-loading issues under ASGI startup.
    from SaveNLoad.models import SimpleUsers
    try:
        return SimpleUsers.objects.get(pk=user_id)
    except SimpleUsers.DoesNotExist:
        return None


def _get_game(game_id):
    """
    Resolve a Game instance (lazy import avoids ASGI app registry issues).
    
    Args:
        game_id: Game ID
    
    Returns:
        Game instance or None
    """
    if not game_id:
        return None
    # Import inside function to avoid app-loading issues under ASGI startup.
    from SaveNLoad.models import Game
    try:
        return Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        return None


def _delete_save_folder_after_delete(user, game, operation_dict):
    """
    Remove SaveFolder row after a successful remote delete.
    
    Args:
        user: SimpleUsers instance
        game: Game instance
        operation_dict: Operation dict from Redis
    
    Returns:
        None
    """
    from SaveNLoad.models.save_folder import SaveFolder
    try:
        # Delete the save folder that matches the operation.
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


def _cleanup_failed_save_folder(operation_id, operation_dict, user, game, error_message):
    """
    Cleanup save folder entries when a save failed due to missing/empty local data.
    
    Args:
        operation_id: Operation identifier
        operation_dict: Operation dict from Redis
        user: SimpleUsers instance
        game: Game instance
        error_message: Failure message
    
    Returns:
        None
    """
    from SaveNLoad.models.save_folder import SaveFolder

    error_lower = error_message.lower() if error_message else ''
    # Only cleanup for known "no files" failure reasons.
    path_errors = [
        'does not exist', 'not found', 'local save path', 'local file not found',
        'local path does not exist', "don't have any save files", "haven't played the game",
        'empty', 'is empty', 'no files', 'no files were transferred', 'no files to save',
        '0 bytes', 'nothing to save', 'contains no valid files', 'appears to be empty'
    ]
    if not any(err in error_lower for err in path_errors):
        return

    try:
        save_folder = SaveFolder.get_by_number(
            user,
            game,
            operation_dict['save_folder_number']
        )
        if not save_folder:
            return

        # Only delete if no other pending/in-progress save ops for this folder.
        other_ops = get_operations_by_user(
            user.id,
            game_id=game.id,
            operation_type='save'
        )
        other_ops = [
            op for op in other_ops
            if op.get('save_folder_number') == operation_dict.get('save_folder_number')
            and op.get('id') != operation_id
        ]

        pending = [op for op in other_ops if op.get('status') in ['pending', 'in_progress']]
        if pending:
            return

        all_failed = all(op.get('status') == 'failed' for op in other_ops)
        if all_failed:
            save_folder.delete()
            print(f"Deleted save folder {save_folder.folder_number} due to failed save operation")
    except Exception as e:
        print(f"WARNING: Failed to cleanup save folder after failed operation: {e}")


def _check_and_handle_game_deletion_completion(operation_dict, game):
    """
    Finalize game deletion once all delete operations are complete.
    
    Args:
        operation_dict: Operation dict from Redis
        game: Game instance
    
    Returns:
        None
    """
    if not (game and game.pending_deletion and
            operation_dict.get('type') == 'delete' and
            not operation_dict.get('save_folder_number')):
        return

    all_operations = get_operations_by_game(game.id)
    game_deletion_ops = [
        op for op in all_operations
        if op.get('type') == 'delete' and not op.get('save_folder_number')
    ]

    remaining = [
        op for op in game_deletion_ops
        if op.get('id') != operation_dict.get('id') and
        op.get('status') in ['pending', 'in_progress']
    ]

    if remaining:
        return

    # If any delete op failed, cancel pending_deletion.
    failed_ops = [op for op in game_deletion_ops if op.get('status') == 'failed']
    all_succeeded = len(failed_ops) == 0

    if all_succeeded:
        game_name = game.name
        game_id = game.id

        # Remove associated banner file before deleting the game.
        _delete_game_banner_file(game)
        game.delete()
        print(f"Game {game_id} ({game_name}) deleted from database after all storage cleanup operations completed successfully")
    else:
        game.pending_deletion = False
        game.save()
        print(f"WARNING: Game {game.id} ({game.name}) deletion cancelled - {len(failed_ops)} storage operation(s) failed")


def _delete_game_banner_file(game):
    """
    Delete the banner file associated with a game.
    Returns: True if deleted successfully or no banner exists, False on error.
    
    Args:
        game: Game instance
    
    Returns:
        bool: True if deleted successfully or no banner exists, False on error
    """
    if not game or not game.banner:
        return True

    try:
        if game.banner.name:
            banner_path = game.banner.path
            if os.path.exists(banner_path):
                os.remove(banner_path)
                print(f"Deleted banner file for game {game.id} ({game.name}): {banner_path}")
            return True
    except Exception as e:
        print(f"WARNING: Failed to delete banner file for game {game.id} ({game.name}): {e}")
        return False

    return True


def _check_and_handle_user_deletion_completion(operation_dict, user):
    """
    Finalize user deletion once all delete operations are complete.
    
    Args:
        operation_dict: Operation dict from Redis
        user: SimpleUsers instance
    
    Returns:
        None
    """
    if not (user and hasattr(user, 'pending_deletion') and user.pending_deletion and
            operation_dict.get('type') == 'delete' and
            not operation_dict.get('game_id') and
            not operation_dict.get('save_folder_number')):
        return

    print(f"DEBUG: Checking user deletion completion for user {user.id} ({user.username})")

    all_operations = get_operations_by_user(
        user.id,
        game_id=None,
        operation_type='delete'
    )

    user_deletion_ops = [op for op in all_operations if not op.get('save_folder_number')]

    print(f"DEBUG: Found {len(user_deletion_ops)} user deletion operations for user {user.id}")

    remaining = [
        op for op in user_deletion_ops
        if op.get('id') != operation_dict.get('id') and
        op.get('status') in ['pending', 'in_progress']
    ]

    if remaining:
        print(f"DEBUG: Still {len(remaining)} pending/in-progress operations for user {user.id}")
        return

    # Only delete the user if every related op succeeded.
    failed_ops = [op for op in user_deletion_ops if op.get('status') == 'failed']
    completed_ops = [op for op in user_deletion_ops if op.get('status') == 'completed']
    total_ops = len(user_deletion_ops)

    all_succeeded = (len(failed_ops) == 0) and (len(completed_ops) == total_ops) and (total_ops > 0)

    print(f"DEBUG: User deletion operations - Total: {total_ops}, Completed: {len(completed_ops)}, Failed: {len(failed_ops)}, All succeeded: {all_succeeded}")

    if all_succeeded:
        username = user.username
        user_id = user.id

        import time
        time.sleep(3)

        user.delete()
        print(f"User {user_id} ({username}) deleted from database after storage cleanup operation completed successfully")
    else:
        user.pending_deletion = False
        user.save()
        print(f"WARNING: User {user.id} ({user.username}) deletion cancelled - {len(failed_ops)} storage operation(s) failed")
