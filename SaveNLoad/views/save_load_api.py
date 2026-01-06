"""
DRF API endpoints for save/load operations.
These endpoints are used by the client worker to perform save/load operations.
"""
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response

from SaveNLoad.services.redis_operation_service import create_operation
from SaveNLoad.utils.datetime_utils import calculate_progress_percentage, to_isoformat
from SaveNLoad.utils.path_utils import generate_game_directory_path, generate_save_folder_path
from SaveNLoad.utils.string_utils import transform_path_error_message
from SaveNLoad.views.api_helpers import (
    parse_json_body,
    get_game_or_error,
    get_client_worker_or_error,
    get_local_save_path_or_error,
    resolve_save_paths_or_error,
    get_save_folder_or_error,
    get_latest_save_folder_or_error,
    validate_save_folder_or_error,
    validate_game_path_mapping_or_error,
    get_game_save_locations,
    create_operation_response,
    json_response_error,
    json_response_success
)
from SaveNLoad.views.custom_decorators import get_current_user


def _build_full_remote_path(username: str, game_name: str, save_folder_number: int,
                            path_index: int = None) -> str:
    """
    Build complete remote FTP path for the client worker.
    This is the ONLY place path construction should happen.

    Args:
        username: User's username.
        game_name: Game name (will be sanitized).
        save_folder_number: Save folder number.
        path_index: Optional path index for multi-path games (1, 2, 3, etc.).

    Returns:
        Complete remote path like "username/GameName/save_1" or "username/GameName/save_1/path_2".
    """
    remote_path = generate_save_folder_path(username, game_name, save_folder_number)

    if path_index is not None:
        remote_path = f"{remote_path}/path_{path_index}"

    return remote_path


@api_view(["POST"])
@authentication_classes([])
def save_game(request, game_id):
    """
    Save game endpoint - queues operation for client worker.
    Expects: {'local_save_path': 'path/to/save/files', 'local_save_paths': ['path1', 'path2'] (optional)}

    If local_save_paths is provided, it will save all locations to separate subfolders (path_1, path_2, etc.).
    """
    from SaveNLoad.models.operation_constants import OperationType

    try:
        user = get_current_user(request)
        if not user:
            return Response(
                {'error': 'Not authenticated. Please log in.', 'requires_login': True},
                status=401
            )

        game, error_response = get_game_or_error(game_id)
        if error_response:
            return error_response

        data, error_response = parse_json_body(request)
        if error_response:
            return error_response

        client_worker, error_response = get_client_worker_or_error(user, request)
        if error_response:
            return error_response

        save_paths, error_response, use_multi_paths = resolve_save_paths_or_error(
            data,
            game,
            require_non_empty_if_provided=True
        )
        if error_response:
            return error_response

        if not use_multi_paths:
            local_save_path, error_response = get_local_save_path_or_error(data, game)
            if error_response:
                return error_response

            from SaveNLoad.models.save_folder import SaveFolder
            save_folder = SaveFolder.get_or_create_next(user, game)
            save_folder, error_response = validate_save_folder_or_error(save_folder)
            if error_response:
                return error_response

            remote_ftp_path = _build_full_remote_path(
                username=user.username,
                game_name=game.name,
                save_folder_number=save_folder.folder_number,
                path_index=None
            )

            operation_id = create_operation(
                {
                    'operation_type': OperationType.SAVE,
                    'user_id': user.id,
                    'game_id': game.id,
                    'local_save_path': local_save_path,
                    'remote_ftp_path': remote_ftp_path,
                    'save_folder_number': save_folder.folder_number,
                },
                client_worker
            )

            return create_operation_response(
                operation_id,
                client_worker,
                extra_data={'save_folder_number': save_folder.folder_number}
            )

        from SaveNLoad.models.save_folder import SaveFolder
        save_folder = SaveFolder.get_or_create_next(user, game)
        save_folder, error_response = validate_save_folder_or_error(save_folder)
        if error_response:
            return error_response

        use_subfolders = len(save_paths) > 1

        operation_ids = []
        for path in save_paths:
            path_index, error_response = validate_game_path_mapping_or_error(
                game,
                path,
                use_subfolders
            )
            if error_response:
                return error_response

            remote_ftp_path = _build_full_remote_path(
                username=user.username,
                game_name=game.name,
                save_folder_number=save_folder.folder_number,
                path_index=path_index
            )

            operation_id = create_operation(
                {
                    'operation_type': OperationType.SAVE,
                    'user_id': user.id,
                    'game_id': game.id,
                    'local_save_path': path,
                    'remote_ftp_path': remote_ftp_path,
                    'save_folder_number': save_folder.folder_number,
                },
                client_worker
            )
            operation_ids.append(operation_id)

        return json_response_success(
            data={
                'operation_ids': operation_ids,
                'save_folder_number': save_folder.folder_number,
                'client_id': client_worker,
                'paths_count': len(save_paths)
            }
        )
    except Exception as e:
        import traceback
        print(f"ERROR in save_game: {e}")
        print(traceback.format_exc())
        return json_response_error(f'Failed to save game: {str(e)}', status=500)


@api_view(["POST"])
@authentication_classes([])
def load_game(request, game_id):
    """
    Load game endpoint - queues operation for client worker.
    Expects: {'local_save_path': 'path/to/save/files', 'local_save_paths': ['path1', 'path2'] (optional),
              'save_folder_number': 1 (optional)}

    If local_save_paths is provided, it will load from separate subfolders (path_1, path_2, etc.).
    """
    from SaveNLoad.models.operation_constants import OperationType

    user = get_current_user(request)
    if not user:
        return Response(
            {'error': 'Not authenticated. Please log in.', 'requires_login': True},
            status=401
        )

    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response

    data, error_response = parse_json_body(request)
    if error_response:
        return error_response

    client_worker, error_response = get_client_worker_or_error(user, request)
    if error_response:
        return error_response

    save_folder_number = data.get('save_folder_number')

    if save_folder_number is None:
        save_folder, error_response = get_latest_save_folder_or_error(user, game)
        if error_response:
            return error_response
        save_folder_number = save_folder.folder_number
    else:
        save_folder, error_response = get_save_folder_or_error(user, game, save_folder_number)
        if error_response:
            return error_response

    load_paths, error_response, use_multi_paths = resolve_save_paths_or_error(data, game)
    if error_response:
        return error_response

    if not use_multi_paths:
        local_save_path, error_response = get_local_save_path_or_error(data, game)
        if error_response:
            return error_response

        remote_ftp_path = _build_full_remote_path(
            username=user.username,
            game_name=game.name,
            save_folder_number=save_folder_number,
            path_index=None
        )

        operation_id = create_operation(
            {
                'operation_type': OperationType.LOAD,
                'user_id': user.id,
                'game_id': game.id,
                'local_save_path': local_save_path,
                'remote_ftp_path': remote_ftp_path,
                'save_folder_number': save_folder_number,
            },
            client_worker
        )

        return create_operation_response(
            operation_id,
            client_worker,
            extra_data={'save_folder_number': save_folder_number}
        )

    use_subfolders = len(load_paths) > 1

    operation_ids = []
    for path in load_paths:
        path_index, error_response = validate_game_path_mapping_or_error(
            game,
            path,
            use_subfolders
        )
        if error_response:
            return error_response

        remote_ftp_path = _build_full_remote_path(
            username=user.username,
            game_name=game.name,
            save_folder_number=save_folder_number,
            path_index=path_index
        )

        operation_id = create_operation(
            {
                'operation_type': OperationType.LOAD,
                'user_id': user.id,
                'game_id': game.id,
                'local_save_path': path,
                'remote_ftp_path': remote_ftp_path,
                'save_folder_number': save_folder_number,
            },
            client_worker
        )
        operation_ids.append(operation_id)

    return json_response_success(
        data={
            'operation_ids': operation_ids,
            'save_folder_number': save_folder_number,
            'client_id': client_worker,
            'paths_count': len(load_paths)
        }
    )


@api_view(["GET"])
@authentication_classes([])
def check_operation_status(request, operation_id):
    """
    Check the status of an operation.
    Admins can check any operation; users can only check their own operations.
    """
    from SaveNLoad.services.redis_operation_service import get_operation, OperationStatus

    user = get_current_user(request)
    if not user:
        return Response(
            {'error': 'Not authenticated. Please log in.', 'requires_login': True},
            status=401
        )

    operation = get_operation(operation_id)
    if not operation:
        is_admin = user.is_admin() if hasattr(user, 'is_admin') else False
        if is_admin:
            return json_response_success(
                data={
                    'status': OperationStatus.COMPLETED,
                    'completed': True,
                    'failed': False,
                    'message': 'Operation completed (operation record may have been cleaned up)',
                    'result_data': None,
                    'progress': {
                        'current': 1,
                        'total': 1,
                        'percentage': 100,
                        'message': 'Completed'
                    }
                }
            )

        return json_response_error('Operation not found', status=404)

    is_admin = user.is_admin() if hasattr(user, 'is_admin') else False
    operation_user_id = operation.get('user_id')
    if operation_user_id:
        try:
            operation_user_id = int(operation_user_id)
        except (ValueError, TypeError):
            operation_user_id = None

    if not is_admin and operation_user_id and operation_user_id != user.id:
        return json_response_error('Operation not found', status=404)

    error_message = None
    status_value = operation.get('status', '')
    if status_value == OperationStatus.FAILED:
        error_msg = operation.get('error_message', '')
        if error_msg:
            error_message = transform_path_error_message(error_msg, operation.get('type', ''))

    progress_current = int(operation.get('progress_current', 0) or 0)
    progress_total = int(operation.get('progress_total', 0) or 0)
    progress_percentage = calculate_progress_percentage(progress_current, progress_total, status_value)

    result_data = None
    if status_value == OperationStatus.COMPLETED:
        result_data_str = operation.get('result_data')
        if result_data_str:
            try:
                import json
                result_data = json.loads(result_data_str) if isinstance(result_data_str, str) else result_data_str
            except Exception:
                result_data = result_data_str

    success_message = None
    if status_value == OperationStatus.COMPLETED:
        operation_type = operation.get('type') or ''
        operation_group = operation.get('operation_group') or ''
        if operation_type == 'delete' and operation_group == 'delete_older':
            success_message = 'Older saves deleted successfully.'
        elif operation_type == 'delete':
            success_message = 'Save deleted successfully.'
        elif operation_type == 'save':
            success_message = 'Game saved successfully.'
        elif operation_type == 'load':
            success_message = 'Game loaded successfully.'
        elif operation_type == 'backup':
            success_message = 'Backup successful.'
        elif operation_type == 'open_folder':
            success_message = 'Folder opened successfully.'
        elif isinstance(result_data, dict):
            success_message = result_data.get('message') or None

    return json_response_success(
        data={
            'status': status_value,
            'completed': status_value == OperationStatus.COMPLETED,
            'failed': status_value == OperationStatus.FAILED,
            'message': error_message if status_value == OperationStatus.FAILED else success_message,
            'result_data': result_data,
            'progress': {
                'current': progress_current,
                'total': progress_total,
                'percentage': progress_percentage,
                'message': operation.get('progress_message', '') or ''
            }
        }
    )


@api_view(["DELETE"])
@authentication_classes([])
def delete_save_folder(request, game_id, folder_number):
    """
    Delete a save folder (from SMB and database).
    """
    user = get_current_user(request)
    if not user:
        return Response(
            {'error': 'Not authenticated. Please log in.', 'requires_login': True},
            status=401
        )

    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response

    from SaveNLoad.models.operation_constants import OperationType

    try:
        save_folder, error_response = get_save_folder_or_error(user, game, folder_number)
        if error_response:
            return error_response

        client_worker, error_response = get_client_worker_or_error(user, request)
        if error_response:
            return error_response

        remote_ftp_path = _build_full_remote_path(
            username=user.username,
            game_name=game.name,
            save_folder_number=folder_number,
            path_index=None
        )

        operation_id = create_operation(
            {
                'operation_type': OperationType.DELETE,
                'user_id': user.id,
                'game_id': game.id,
                'local_save_path': '',
                'remote_ftp_path': remote_ftp_path,
                'save_folder_number': folder_number,
            },
            client_worker
        )

        return create_operation_response(
            operation_id,
            client_worker,
            extra_data={'save_folder_number': folder_number}
        )

    except Exception as e:
        print(f"ERROR: Failed to delete save folder: {e}")
        return json_response_error(f'Failed to delete save folder: {str(e)}', status=500)


@api_view(["GET"])
@authentication_classes([])
def list_save_folders(request, game_id):
    """
    List all available save folders for a game with their dates (sorted by latest).
    """
    user = get_current_user(request)
    if not user:
        return Response(
            {'error': 'Not authenticated. Please log in.', 'requires_login': True},
            status=401
        )

    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response

    from SaveNLoad.models.save_folder import SaveFolder
    from SaveNLoad.utils.model_utils import filter_by_user_and_game

    save_folders = filter_by_user_and_game(SaveFolder, user, game).order_by('-created_at')

    folders_data = []
    for folder in save_folders:
        folders_data.append({
            'folder_number': folder.folder_number,
            'folder_name': folder.folder_name,
            'created_at': to_isoformat(folder.created_at),
            'updated_at': to_isoformat(folder.updated_at)
        })

    return json_response_success(
        data={'save_folders': folders_data}
    )


@api_view(["POST"])
@authentication_classes([])
def backup_all_saves(request, game_id):
    """
    Backup all save files for a game - queues operation for client worker.
    """
    from SaveNLoad.models.operation_constants import OperationType

    user = get_current_user(request)
    if not user:
        return Response(
            {'error': 'Not authenticated. Please log in.', 'requires_login': True},
            status=401
        )

    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response

    client_worker, error_response = get_client_worker_or_error(user, request)
    if error_response:
        return error_response

    remote_ftp_path = generate_game_directory_path(user.username, game.name)

    operation_id = create_operation(
        {
            'operation_type': OperationType.BACKUP,
            'user_id': user.id,
            'game_id': game.id,
            'local_save_path': '',
            'remote_ftp_path': remote_ftp_path,
            'save_folder_number': None,
        },
        client_worker
    )

    return create_operation_response(
        operation_id,
        client_worker
    )


@api_view(["DELETE"])
@authentication_classes([])
def delete_all_saves(request, game_id):
    """
    Delete all save folders for a game except the latest one (from SMB and database).
    """
    user = get_current_user(request)
    if not user:
        return Response(
            {'error': 'Not authenticated. Please log in.', 'requires_login': True},
            status=401
        )

    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response

    from SaveNLoad.models.operation_constants import OperationType
    from SaveNLoad.utils.model_utils import filter_by_user_and_game
    from SaveNLoad.models.save_folder import SaveFolder

    try:
        save_folders = filter_by_user_and_game(SaveFolder, user, game)

        if not save_folders.exists():
            return json_response_error('No save folders found for this game', status=404)

        latest_save = SaveFolder.get_latest(user, game)
        if not latest_save:
            return json_response_error('No save folders found for this game', status=404)

        save_folders = save_folders.exclude(id=latest_save.id)
        if not save_folders.exists():
            return json_response_error('No older save folders found for this game', status=404)

        client_worker, error_response = get_client_worker_or_error(user, request)
        if error_response:
            return error_response

        operation_ids = []
        invalid_folders = []

        for save_folder in save_folders:
            try:
                validated_folder, error_response = validate_save_folder_or_error(save_folder)
                if error_response:
                    print(
                        f'WARNING: Save folder {save_folder.id} validation failed: '
                        f'{error_response.data if hasattr(error_response, "data") else "validation error"}, skipping'
                    )
                    invalid_folders.append(save_folder)
                    continue

                remote_ftp_path = _build_full_remote_path(
                    username=user.username,
                    game_name=game.name,
                    save_folder_number=save_folder.folder_number,
                    path_index=None
                )

                operation_id = create_operation(
                    {
                        'operation_type': OperationType.DELETE,
                        'operation_group': 'delete_older',
                        'user_id': user.id,
                        'game_id': game.id,
                        'local_save_path': '',
                        'remote_ftp_path': remote_ftp_path,
                        'save_folder_number': save_folder.folder_number,
                    },
                    client_worker
                )
                operation_ids.append(operation_id)

            except Exception as e:
                print(f"ERROR: Failed to create delete operation for save folder {save_folder.folder_number}: {e}")
                invalid_folders.append(save_folder)

        for save_folder in invalid_folders:
            try:
                save_folder.delete()
            except Exception:
                pass

        if not operation_ids:
            if invalid_folders:
                return json_response_error('No valid save folders found to delete', status=404)
            return json_response_error('No older save folders found for this game', status=404)

        return json_response_success(
            data={
                'operation_ids': operation_ids,
                'total_count': len(operation_ids),
                'client_id': client_worker
            }
        )

    except Exception as e:
        print(f"ERROR: Failed to delete all saves: {e}")
        return json_response_error(f'Failed to delete all saves: {str(e)}', status=500)


@api_view(["GET"])
@authentication_classes([])
def get_game_save_location(request, game_id):
    """
    Get the save file location for a game.
    """
    user = get_current_user(request)
    if not user:
        return Response(
            {'error': 'Not authenticated. Please log in.', 'requires_login': True},
            status=401
        )

    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response

    save_paths = get_game_save_locations(game)
    return json_response_success(
        data={
            'save_file_location': save_paths[0] if save_paths else '',
            'save_file_locations': save_paths,
            'game_name': game.name
        }
    )


@api_view(["POST"])
@authentication_classes([])
def open_save_location(request, game_id):
    """
    Open the save file location for a game - queues operation for client worker.
    Creates local folders if they don't exist, then opens them.
    Handles multiple save paths by opening all of them.
    """
    from SaveNLoad.models.operation_constants import OperationType
    import json

    user = get_current_user(request)
    if not user:
        return Response(
            {'error': 'Not authenticated. Please log in.', 'requires_login': True},
            status=401
        )

    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response

    client_worker, error_response = get_client_worker_or_error(user, request)
    if error_response:
        return error_response

    save_paths = get_game_save_locations(game)

    if not save_paths:
        return json_response_error('No save file location found for this game', status=400)

    paths_data = {
        'paths': save_paths,
        'create_folders': True
    }
    paths_json = json.dumps(paths_data)

    operation_id = create_operation(
        {
            'operation_type': OperationType.OPEN_FOLDER,
            'user_id': user.id,
            'game_id': game.id,
            'local_save_path': paths_json,
            'save_folder_number': None,
            'smb_path': None,
            'path_index': None
        },
        client_worker
    )

    path_count = len(save_paths)
    return create_operation_response(
        operation_id,
        client_worker
    )


@api_view(["POST"])
@authentication_classes([])
def open_backup_location(request, game_id):
    """
    Open the folder that contains a backup zip file.
    """
    from SaveNLoad.models.operation_constants import OperationType
    import json
    from pathlib import PurePosixPath, PureWindowsPath
    import os

    user = get_current_user(request)
    if not user:
        return Response(
            {'error': 'Not authenticated. Please log in.', 'requires_login': True},
            status=401
        )

    game, error_response = get_game_or_error(game_id)
    if error_response:
        return error_response

    data, error_response = parse_json_body(request)
    if error_response:
        return error_response

    zip_path = (data.get('zip_path') or '').strip()
    if not zip_path:
        return json_response_error('zip_path is required', status=400)

    posix_folder = str(PurePosixPath(zip_path).parent)
    windows_folder = str(PureWindowsPath(zip_path).parent)
    folder_path = windows_folder or posix_folder
    if not folder_path or folder_path == '.':
        return json_response_error('Invalid zip_path', status=400)

    client_worker, error_response = get_client_worker_or_error(user, request)
    if error_response:
        return error_response

    paths_data = {
        'paths': [folder_path],
        'create_folders': False
    }
    paths_json = json.dumps(paths_data)

    operation_id = create_operation(
        {
            'operation_type': OperationType.OPEN_FOLDER,
            'user_id': user.id,
            'game_id': game.id,
            'local_save_path': paths_json,
            'save_folder_number': None,
            'smb_path': None,
            'path_index': None
        },
        client_worker
    )

    return create_operation_response(
        operation_id,
        client_worker
    )
