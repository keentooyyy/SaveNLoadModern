"""
DRF API endpoints for client worker registration and communication.
"""
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from SaveNLoad.models import SimpleUsers
from SaveNLoad.services.redis_worker_service import (
    register_worker,
    get_worker_info,
    get_worker_claim_data,
    claim_worker as redis_claim_worker,
    unclaim_worker as redis_unclaim_worker,
    is_worker_online,
    get_workers_snapshot,
    issue_ws_token,
)
from SaveNLoad.views.api_helpers import (
    parse_json_body,
    json_response_error,
    json_response_success
)
from SaveNLoad.views.custom_decorators import get_current_user


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def register_client(request):
    """
    Register a client worker - client_id must be unique per PC.
    """
    try:
        data, error_response = parse_json_body(request)
        if error_response:
            return error_response

        client_id = (data.get('client_id') or '').strip()

        if not client_id:
            return json_response_error('client_id is required', status=400)

        user_id, linked_user = get_worker_claim_data(client_id)

        register_worker(client_id, user_id)
        ws_token = issue_ws_token(client_id)

        if user_id and not linked_user:
            try:
                user = SimpleUsers.objects.get(pk=user_id)
                linked_user = user.username
            except SimpleUsers.DoesNotExist:
                linked_user = None

        print(f"Client worker registered: {client_id} linked_user={linked_user} user_id={user_id}")
        return json_response_success(
            message='Client worker registered successfully',
            data={
                'client_id': client_id,
                'linked_user': linked_user,
                'ws_token': ws_token
            }
        )

    except Exception as e:
        print(f"ERROR: Failed to register client: {e}")
        return json_response_error('Failed to register client', status=500)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def unregister_client(request):
    """
    Unregister a client worker (called on shutdown).
    """
    try:
        data, error_response = parse_json_body(request)
        if error_response:
            return error_response

        client_id = (data.get('client_id') or '').strip()

        print(f"Client worker unregistered: {client_id}")
        return json_response_success(message='Client worker unregistered')

    except Exception as e:
        print(f"ERROR: Failed to unregister client: {e}")
        return json_response_error('Failed to unregister client', status=500)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def get_unpaired_workers(request):
    """
    Get list of all online workers with their claim status.
    """
    user = get_current_user(request)
    if not user:
        return Response(
            {'error': 'Not authenticated. Please log in.', 'requires_login': True},
            status=401
        )

    return json_response_success(
        data={'workers': get_workers_snapshot()}
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def claim_worker(request):
    """
    Claim a worker for the current user.
    """
    try:
        user = get_current_user(request)
        if not user:
            return Response(
                {'error': 'Not authenticated. Please log in.', 'requires_login': True},
                status=401
            )

        data, error_response = parse_json_body(request)
        if error_response:
            return error_response

        client_id = (data.get('client_id') or '').strip()
        if not client_id:
            return json_response_error('client_id is required', status=400)

        if not is_worker_online(client_id):
            return json_response_error('Worker not found or offline', status=404)

        worker_info = get_worker_info(client_id)
        if worker_info and worker_info.get('user_id') and worker_info['user_id'] != user.id:
            return json_response_error('Worker is already claimed by another user', status=409)

        success = redis_claim_worker(client_id, user.id, username=user.username)
        if not success:
            return json_response_error('Failed to claim worker', status=500)

        print(f"Worker {client_id} claimed by {user.username} user_id={user.id}")
        return json_response_success(message='Worker claimed successfully')

    except Exception as e:
        print(f"ERROR: Failed to claim worker: {e}")
        return json_response_error('Failed to claim worker', status=500)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def unclaim_worker(request):
    """
    Unclaim a worker (release ownership).
    """
    try:
        user = get_current_user(request)
        if not user:
            return Response(
                {'error': 'Not authenticated. Please log in.', 'requires_login': True},
                status=401
            )

        data, error_response = parse_json_body(request)
        if error_response:
            return error_response

        client_id = (data.get('client_id') or '').strip()
        if not client_id:
            return json_response_error('client_id is required', status=400)

        worker_info = get_worker_info(client_id)
        if not worker_info:
            return json_response_error('Worker not found', status=404)

        if not worker_info.get('user_id') or worker_info['user_id'] != user.id:
            return json_response_error('Worker not found or not owned by you', status=404)

        redis_unclaim_worker(client_id)

        print(f"Worker {client_id} unclaimed by {user.username} user_id={user.id}")
        return json_response_success(message='Worker unclaimed successfully')

    except Exception as e:
        print(f"ERROR: Failed to unclaim worker: {e}")
        return json_response_error('Failed to unclaim worker', status=500)
