"""
API endpoints for client worker registration and communication
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

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


@csrf_exempt
@require_http_methods(["POST"])
def register_client(request):
    """
    Register a client worker - client_id must be unique per PC.

    Args:
        request: Django request object.

    Returns:
        JsonResponse with worker registration details.
    """
    try:
        data, error_response = parse_json_body(request)
        if error_response:
            return error_response

        client_id = data.get('client_id', '').strip()

        if not client_id:
            return json_response_error('client_id is required', status=400)

        # Get claim data even if the worker was offline (heartbeat missing).
        user_id, linked_user = get_worker_claim_data(client_id)

        # Register worker (creates or updates) - no auto-claiming, user must manually claim via frontend
        register_worker(client_id, user_id)
        ws_token = issue_ws_token(client_id)

        # Get linked user username if exists
        if user_id:
            if not linked_user:
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
        return json_response_error(str(e), status=500)


@csrf_exempt
@require_http_methods(["POST"])
def unregister_client(request):
    """
    Unregister a client worker (called on shutdown).

    Args:
        request: Django request object.

    Returns:
        JsonResponse with status message.
    """
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
def get_unpaired_workers(request):
    """
    Get list of all online workers with their claim status.

    Args:
        request: Django request object.

    Returns:
        JsonResponse containing worker snapshot list.
    """
    from SaveNLoad.views.custom_decorators import get_current_user

    user = get_current_user(request)
    if not user:
        return json_response_error('Authentication required', status=401)

    return JsonResponse({
        'workers': get_workers_snapshot()
    })


@csrf_exempt
@require_http_methods(["POST"])
def claim_worker(request):
    """
    Claim a worker for the current user.

    Args:
        request: Django request object.

    Returns:
        JsonResponse with claim status.
    """
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

        # Claim it - pass username so client worker can display it
        success = redis_claim_worker(client_id, user.id, username=user.username)
        if not success:
            return json_response_error('Failed to claim worker', status=500)

        print(f"Worker {client_id} claimed by {user.username} user_id={user.id}")
        return json_response_success(message='Worker claimed successfully')

    except Exception as e:
        print(f"ERROR: Failed to claim worker: {e}")
        return json_response_error(str(e), status=500)


@csrf_exempt
@require_http_methods(["POST"])
def unclaim_worker(request):
    """
    Unclaim a worker (release ownership).

    Args:
        request: Django request object.

    Returns:
        JsonResponse with unclaim status.
    """
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

        print(f"Worker {client_id} unclaimed by {user.username} user_id={user.id}")
        return json_response_success(message='Worker unclaimed successfully')

    except Exception as e:
        print(f"ERROR: Failed to unclaim worker: {e}")
        return json_response_error(str(e), status=500)
"""
DEPRECATED: Legacy Django function views retained for reference only.
Do not use in production; replaced by DRF API views.
"""
