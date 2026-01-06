"""
DRF API endpoints for settings and admin operations.
"""
import os
from urllib.parse import urlparse

from django.core.files import File
from django.db import models
from rest_framework.decorators import api_view, authentication_classes
from django.views.decorators.csrf import csrf_protect
from rest_framework.response import Response

from SaveNLoad.models import Game
from SaveNLoad.utils.image_utils import download_image_from_url, get_image_url_or_fallback, is_local_url
from SaveNLoad.views.api_helpers import (
    parse_json_body,
    check_admin_or_error,
    json_response_error,
    json_response_success,
    normalize_save_file_locations,
    validate_unique_save_file_locations,
    cleanup_operations_by_status,
    cleanup_operations_by_age
)
from SaveNLoad.views.custom_decorators import get_current_user
from SaveNLoad.views.rawg_api import search_games as rawg_search_games


def _require_user(request):
    user = get_current_user(request)
    if not user:
        return None, Response(
            {'error': 'Not authenticated. Please log in.', 'requires_login': True},
            status=401
        )
    return user, None


@api_view(["GET"])
@authentication_classes([])
def search_game(request):
    """
    Search RAWG for games by name (Admin only).
    """
    user, error_response = _require_user(request)
    if error_response:
        return error_response

    if not user.is_admin():
        return json_response_error('Unauthorized', status=403)

    from SaveNLoad.views.input_sanitizer import sanitize_search_query

    raw_query = request.GET.get('q', '').strip()
    query = sanitize_search_query(raw_query) if raw_query else None

    if not query:
        return json_response_success(data={'games': []})

    try:
        games = rawg_search_games(query=query, limit=15)

        results = []
        for game in games:
            results.append(
                {
                    'id': game.get('id'),
                    'name': game.get('title') or game.get('name') or 'Unknown',
                    'banner': game.get('image') or '',
                    'save_file_locations': [],
                    'year': game.get('year', ''),
                    'company': game.get('company', ''),
                }
            )

        return json_response_success(data={'games': results})
    except Exception as e:
        print(f"ERROR: Error in search_game view: {e}")
        return json_response_error('Failed to search games', status=500)


@api_view(["POST"])
@authentication_classes([])
@csrf_protect
def create_game(request):
    """
    Create a new game (Admin only).
    """
    user, error_response = _require_user(request)
    if error_response:
        return error_response

    error_response = check_admin_or_error(user)
    if error_response:
        return error_response

    try:
        data, error_response = parse_json_body(request)
        if error_response:
            return error_response

        name = (data.get('name') or '').strip()
        save_file_locations = normalize_save_file_locations(data)
        banner = (data.get('banner') or '').strip()

        if not name or not save_file_locations:
            return json_response_error('Game name and at least one save file location are required.', status=400)

        if not save_file_locations:
            return json_response_error('At least one valid save file location is required.', status=400)

        duplicate_error = validate_unique_save_file_locations(save_file_locations)
        if duplicate_error:
            return duplicate_error

        if Game.objects.filter(name=name).exists():
            return json_response_error('A game with this name already exists.', status=400)

        game_data = {
            'name': name,
            'save_file_locations': save_file_locations,
        }

        if banner:
            game_data['banner_url'] = banner

        game = Game.objects.create(**game_data)

        game.generate_path_mappings()

        if banner:
            if is_local_url(banner, request):
                print(f"Banner URL is local ({banner}) - skipping download")
            else:
                try:
                    success, message, file_obj = download_image_from_url(banner, timeout=10)
                    if success and file_obj:
                        try:
                            parsed = urlparse(banner)
                            ext = os.path.splitext(parsed.path)[1] or '.jpg'
                            game.banner.save(f"banner_{game.id}{ext}", File(file_obj), save=True)
                            game.refresh_from_db()
                            if game.banner:
                                local_url = request.build_absolute_uri(game.banner.url) if request else game.banner.url
                                game.banner_url = local_url
                                game.save(update_fields=['banner_url'])
                            if hasattr(file_obj, 'name'):
                                os.unlink(file_obj.name)
                            print(
                                f"Successfully downloaded and cached banner for game {game.id}: "
                                f"{game.banner.name if game.banner else 'NOT SET'}"
                            )
                        except Exception as e:
                            print(f"ERROR: Failed to save cached banner for game {game.id}: {e}")
                    else:
                        print(f"WARNING: Failed to download banner for game {game.id}: {message}")
                except Exception as e:
                    print(f"ERROR: Banner download failed for game {game.id}: {e}")

        return json_response_success(
            message=f'Game "{game.name}" created successfully!',
            data={
                'game': {
                    'id': game.id,
                    'name': game.name,
                    'banner': get_image_url_or_fallback(game, request),
                    'save_file_locations': game.save_file_locations,
                }
            }
        )
    except Exception as e:
        print(f"ERROR: Error creating game: {str(e)}")
        return json_response_error('Failed to create game', status=500)


@api_view(["POST"])
@authentication_classes([])
@csrf_protect
def update_account_settings(request):
    """
    Update account settings (email and/or password).
    """
    user, error_response = _require_user(request)
    if error_response:
        return error_response

    data, error_response = parse_json_body(request)
    if error_response:
        return error_response

    from SaveNLoad.views.input_sanitizer import sanitize_email, validate_password_strength

    raw_email = data.get('email', '').strip()
    email = sanitize_email(raw_email) if raw_email else None

    if raw_email and not email:
        return json_response_error('Invalid email format.', status=400)

    current_password = data.get('current_password', '').strip()
    new_password = data.get('new_password', '').strip()
    confirm_password = data.get('confirm_password', '').strip()

    if current_password:
        is_valid, error_msg = validate_password_strength(current_password)
        if not is_valid:
            return json_response_error(f'Current password: {error_msg}', status=400)
        if '\x00' in current_password:
            return json_response_error('Invalid characters in current password.', status=400)

    if new_password:
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            return json_response_error(f'New password: {error_msg}', status=400)
        if '\x00' in new_password:
            return json_response_error('Invalid characters in new password.', status=400)

    if confirm_password:
        is_valid, error_msg = validate_password_strength(confirm_password)
        if not is_valid:
            return json_response_error(f'Confirm password: {error_msg}', status=400)
        if '\x00' in confirm_password:
            return json_response_error('Invalid characters in confirm password.', status=400)

    messages = []
    email_changed = False
    password_changed = False

    if email:
        if email.lower() != user.email.lower():
            from SaveNLoad.models import SimpleUsers
            if SimpleUsers.objects.filter(email__iexact=email).exclude(id=user.id).exists():
                return json_response_error('This email is already in use by another account.', status=400)

            user.email = email
            email_changed = True
            messages.append('Email updated successfully')

    if current_password or new_password or confirm_password:
        if not current_password:
            return json_response_error('Current password is required to change password.', status=400)
        if not new_password:
            return json_response_error('New password is required.', status=400)
        if not confirm_password:
            return json_response_error('Please confirm your new password.', status=400)

        if not user.check_password(current_password):
            return json_response_error('Current password is incorrect.', status=400)

        if new_password != confirm_password:
            return json_response_error('New passwords do not match.', status=400)

        if user.check_password(new_password):
            return json_response_error('New password must be different from current password.', status=400)

        user.set_password(new_password)
        password_changed = True
        messages.append('Password changed successfully')

    if email_changed or password_changed:
        user.save()
        message = ' and '.join(messages) + '!'
        return json_response_success(message=message)

    return json_response_success(message='No changes made.')


@api_view(["GET"])
@authentication_classes([])
def operation_queue_stats(request):
    """
    Get statistics about the operation queue (Admin only).
    """
    user, error_response = _require_user(request)
    if error_response:
        return error_response

    error_response = check_admin_or_error(user)
    if error_response:
        return error_response

    from SaveNLoad.utils.redis_client import get_redis_client
    from SaveNLoad.services.redis_operation_service import OperationStatus
    from SaveNLoad.models.operation_constants import OperationType
    from django.utils import timezone
    from datetime import timedelta

    redis_client = get_redis_client()

    operation_keys = redis_client.keys('operation:*')

    all_operations = []
    for key in operation_keys:
        operation_hash = redis_client.hgetall(key)
        if operation_hash:
            all_operations.append({
                'status': operation_hash.get('status', ''),
                'type': operation_hash.get('type', ''),
                'created_at': operation_hash.get('created_at', ''),
                'started_at': operation_hash.get('started_at', '')
            })

    total_count = len(all_operations)

    status_counts = {
        OperationStatus.PENDING: 0,
        OperationStatus.IN_PROGRESS: 0,
        OperationStatus.COMPLETED: 0,
        OperationStatus.FAILED: 0,
    }
    for op in all_operations:
        status_value = op.get('status', '')
        if status_value in status_counts:
            status_counts[status_value] += 1

    type_counts = {
        OperationType.SAVE: 0,
        OperationType.LOAD: 0,
        OperationType.LIST: 0,
        OperationType.DELETE: 0,
        OperationType.BACKUP: 0,
        OperationType.OPEN_FOLDER: 0,
    }
    for op in all_operations:
        op_type = op.get('type', '')
        if op_type in type_counts:
            type_counts[op_type] += 1

    oldest = None
    newest = None
    if all_operations:
        sorted_ops = sorted(all_operations, key=lambda x: x.get('created_at', ''))
        oldest = sorted_ops[0] if sorted_ops else None
        newest = sorted_ops[-1] if sorted_ops else None

    thirty_days_ago = timezone.now() - timedelta(days=30)
    old_count = 0
    for op in all_operations:
        created_at_str = op.get('created_at')
        if created_at_str:
            try:
                from datetime import datetime
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                if timezone.is_aware(created_at):
                    created_at = timezone.make_naive(created_at)
                if created_at < timezone.make_naive(thirty_days_ago):
                    old_count += 1
            except Exception:
                pass

    seven_days_ago = timezone.now() - timedelta(days=7)
    week_old_count = 0
    for op in all_operations:
        created_at_str = op.get('created_at')
        if created_at_str:
            try:
                from datetime import datetime
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                if timezone.is_aware(created_at):
                    created_at = timezone.make_naive(created_at)
                if created_at < timezone.make_naive(seven_days_ago):
                    week_old_count += 1
            except Exception:
                pass

    one_hour_ago = timezone.now() - timedelta(hours=1)
    stuck_count = 0
    for op in all_operations:
        if op.get('status') == OperationStatus.IN_PROGRESS:
            started_at_str = op.get('started_at')
            if started_at_str:
                try:
                    from datetime import datetime
                    started_at = datetime.fromisoformat(started_at_str.replace('Z', '+00:00'))
                    if timezone.is_aware(started_at):
                        started_at = timezone.make_naive(started_at)
                    if started_at < timezone.make_naive(one_hour_ago):
                        stuck_count += 1
                except Exception:
                    pass

    stats = {
        'total': total_count,
        'by_status': {
            'pending': status_counts.get(OperationStatus.PENDING, 0),
            'in_progress': status_counts.get(OperationStatus.IN_PROGRESS, 0),
            'completed': status_counts.get(OperationStatus.COMPLETED, 0),
            'failed': status_counts.get(OperationStatus.FAILED, 0),
        },
        'by_type': {
            'save': type_counts.get(OperationType.SAVE, 0),
            'load': type_counts.get(OperationType.LOAD, 0),
            'list': type_counts.get(OperationType.LIST, 0),
            'delete': type_counts.get(OperationType.DELETE, 0),
        },
        'oldest_operation': oldest.get('created_at') if oldest else None,
        'newest_operation': newest.get('created_at') if newest else None,
        'old_count_30_days': old_count,
        'old_count_7_days': week_old_count,
        'stuck_count': stuck_count,
    }

    return json_response_success(data=stats)


@api_view(["POST"])
@authentication_classes([])
@csrf_protect
def operation_queue_cleanup(request):
    """
    Cleanup operation queue (Admin only).
    """
    user, error_response = _require_user(request)
    if error_response:
        return error_response

    error_response = check_admin_or_error(user)
    if error_response:
        return error_response

    from SaveNLoad.utils.redis_client import get_redis_client
    from SaveNLoad.services.redis_operation_service import OperationStatus

    data, error_response = parse_json_body(request)
    if error_response:
        return error_response

    cleanup_type = data.get('type', '').strip()

    if cleanup_type == 'completed':
        return cleanup_operations_by_status(
            status=OperationStatus.COMPLETED,
            no_items_message='No completed operations to delete',
            success_message_template='Deleted {count} completed operation(s)'
        )

    if cleanup_type == 'failed':
        return cleanup_operations_by_status(
            status=OperationStatus.FAILED,
            no_items_message='No failed operations to delete',
            success_message_template='Deleted {count} failed operation(s)'
        )

    if cleanup_type == 'old':
        return cleanup_operations_by_age(
            days=30,
            no_items_message='No old operations (30+ days) to delete',
            success_message_template='Deleted {count} old operation(s) (30+ days)'
        )

    if cleanup_type == 'all':
        redis_client = get_redis_client()
        operation_keys = redis_client.keys('operation:*')
        deleted_count = len(operation_keys)

        for key in operation_keys:
            redis_client.delete(key)

        if deleted_count == 0:
            return json_response_success(
                message='No operations to delete - queue is empty',
                data={'deleted_count': 0}
            )

        return json_response_success(
            message=f'Deleted all {deleted_count} operation(s)',
            data={'deleted_count': deleted_count}
        )

    return json_response_error('Invalid cleanup type. Must be: completed, failed, old, or all', status=400)


@api_view(["GET"])
@authentication_classes([])
def list_users(request):
    """
    List all users with pagination (Admin only).
    """
    user, error_response = _require_user(request)
    if error_response:
        return error_response

    error_response = check_admin_or_error(user)
    if error_response:
        return error_response

    try:
        from SaveNLoad.models import SimpleUsers

        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 25))

        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 25
        if page_size > 100:
            page_size = 100

        search_query = request.GET.get('q', '').strip()

        users_query = SimpleUsers.objects.all().exclude(id=user.id).order_by('username')

        if search_query:
            users_query = users_query.filter(
                models.Q(username__icontains=search_query) |
                models.Q(email__icontains=search_query)
            )

        total_count = users_query.count()
        total_pages = (total_count + page_size - 1) // page_size

        if page > total_pages and total_pages > 0:
            page = total_pages

        offset = (page - 1) * page_size
        users = users_query[offset:offset + page_size]

        users_list = []
        for u in users:
            users_list.append({
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'role': u.role,
            })

        return json_response_success(
            data={
                'users': users_list,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_previous': page > 1,
                }
            }
        )
    except Exception as e:
        print(f"ERROR: Error listing users: {str(e)}")
        return json_response_error('Failed to list users', status=500)


def _queue_user_deletion_operations(user, admin_user, request=None):
    """
    Queue operations to delete all FTP saves for a user before deletion.
    """
    from SaveNLoad.models.save_folder import SaveFolder
    from SaveNLoad.models.operation_constants import OperationType
    from SaveNLoad.services.redis_operation_service import create_operation

    try:
        save_folders = SaveFolder.objects.filter(user=user)

        if not save_folders.exists():
            print(f"No save folders found for user {user.id} ({user.username}), no FTP cleanup needed")
            return (True, "no_saves", None)

        from SaveNLoad.views.api_helpers import get_client_worker_or_error
        client_worker, error_response = get_client_worker_or_error(admin_user, request)
        if error_response:
            error_msg = (
                f"No active client worker available. Cannot delete FTP saves for user '{user.username}'. "
                "Please ensure a client worker is running and try again."
            )
            print(
                f"WARNING: No active client worker available for admin {admin_user.username}, "
                f"cannot delete FTP saves for user {user.id}"
            )
            return (False, error_msg, None)

        operation_id = create_operation(
            {
                'operation_type': OperationType.DELETE,
                'operation_group': 'user_delete',
                'user_id': user.id,
                'game_id': None,
                'local_save_path': '',
                'save_folder_number': None,
                'remote_ftp_path': user.username,
                'smb_path': user.username,
                'path_index': None
            },
            client_worker
        )

        print(
            f"Queued delete operation for user directory: {user.username}/ "
            f"(assigned to admin's worker: {client_worker})"
        )
        return (True, None, operation_id)
    except Exception as e:
        error_msg = f"Error queueing user deletion operations: {str(e)}"
        print(f"ERROR: Error queueing user deletion operations for user {user.id}: {e}")
        return (False, error_msg, None)


def _handle_user_deletion(request, user, admin_user):
    """
    Helper to handle user deletion logic.
    """
    success, error_message, operation_id = _queue_user_deletion_operations(
        user,
        admin_user=admin_user,
        request=request
    )
    if not success:
        return json_response_error(error_message or "Failed to queue FTP cleanup operations", status=503)

    if error_message == "no_saves":
        user.delete()
        print(f"User {user.id} ({user.username}) deleted immediately - no FTP saves to clean up")
        return json_response_success(message=f'User "{user.username}" deleted successfully')

    user.pending_deletion = True
    user.save()
    print(
        f"User {user.id} ({user.username}) marked for deletion - "
        "will be deleted after FTP cleanup operation completes"
    )
    return json_response_success(
        message=f'User "{user.username}" deletion queued. FTP cleanup in progress...',
        data={'operation_id': operation_id}
    )


@api_view(["DELETE", "POST"])
@authentication_classes([])
@csrf_protect
def delete_user(request, user_id):
    """
    Delete a user account (Admin only).
    """
    admin_user, error_response = _require_user(request)
    if error_response:
        return error_response

    error_response = check_admin_or_error(admin_user)
    if error_response:
        return error_response

    try:
        from SaveNLoad.models import SimpleUsers

        try:
            target_user = SimpleUsers.objects.get(id=user_id)
        except SimpleUsers.DoesNotExist:
            return json_response_error('User not found.', status=404)

        if target_user.id == admin_user.id:
            return json_response_error('You cannot delete your own account.', status=400)

        return _handle_user_deletion(request, target_user, admin_user)
    except Exception as e:
        print(f"ERROR: Error deleting user: {str(e)}")
        return json_response_error('Failed to delete user', status=500)


@api_view(["POST"])
@authentication_classes([])
@csrf_protect
def reset_user_password(request, user_id):
    """
    Reset a user's password to default constant (Admin only).
    """
    user, error_response = _require_user(request)
    if error_response:
        return error_response

    error_response = check_admin_or_error(user)
    if error_response:
        return error_response

    try:
        from SaveNLoad.models import SimpleUsers
        from SaveNLoad.views.input_sanitizer import validate_password_strength

        try:
            target_user = SimpleUsers.objects.get(id=user_id)
        except SimpleUsers.DoesNotExist:
            return json_response_error('User not found.', status=404)

        if target_user.id == user.id:
            return json_response_error(
                'You cannot reset your own password through this feature.',
                status=400
            )

        default_password = os.getenv('RESET_PASSWORD_DEFAULT')

        is_valid, error_msg = validate_password_strength(default_password)
        if not is_valid:
            return json_response_error(f'Default password validation failed: {error_msg}', status=500)

        target_user.set_password(default_password)
        target_user.save()

        return json_response_success(
            message=(
                f'Password reset successfully for user "{target_user.username}". '
                'Default password has been set.'
            ),
            data={
                'user': {
                    'id': target_user.id,
                    'username': target_user.username,
                    'email': target_user.email,
                },
            }
        )
    except Exception as e:
        print(f"ERROR: Error resetting user password: {str(e)}")
        return json_response_error('Failed to reset password', status=500)
