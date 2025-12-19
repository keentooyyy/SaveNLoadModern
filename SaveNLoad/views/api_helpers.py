"""
Common helper functions for API endpoints
"""
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from SaveNLoad.models import Game
from SaveNLoad.models.client_worker import ClientWorker
from SaveNLoad.models.operation_queue import OperationQueue, OperationType
from SaveNLoad.views.custom_decorators import get_current_user
from django.utils import timezone
from datetime import timedelta
import json
import logging

logger = logging.getLogger(__name__)


def json_response_error(message: str, status: int = 400) -> JsonResponse:
    """Helper to create error JSON responses"""
    return JsonResponse({'error': message}, status=status)


def json_response_success(message: str = None, data: dict = None) -> JsonResponse:
    """Helper to create success JSON responses"""
    response = {'success': True}
    if message:
        response['message'] = message
    if data:
        response.update(data)
    return JsonResponse(response)


def parse_json_body(request):
    """
    Parse JSON body from request
    Returns: (data_dict, error_response_or_none)
    """
    try:
        data = json.loads(request.body or "{}")
        return data, None
    except json.JSONDecodeError:
        return {}, json_response_error('Invalid JSON body', status=400)


def get_game_or_error(game_id):
    """
    Get game by ID or return error response
    Returns: (game_object, error_response_or_none)
    """
    try:
        game = Game.objects.get(pk=game_id)
        return game, None
    except Game.DoesNotExist:
        return None, json_response_error('Game not found', status=404)


def get_client_worker_or_error(client_id=None, user=None):
    """
    Get client worker for a user or return error response
    Priority: 1) specified client_id, 2) user's worker (from recent operations)
    Returns: (client_worker_object, error_response_or_none)
    
    Note: App requires workers to function, so we don't fall back to "any worker"
    """
    if client_id:
        # Use specified client worker
        try:
            client_worker = ClientWorker.objects.get(client_id=client_id, is_active=True)
            if not client_worker.is_online():
                return None, json_response_error('Specified client worker is not online', status=400)
            return client_worker, None
        except ClientWorker.DoesNotExist:
            return None, json_response_error('Specified client worker not found', status=400)
    
    # Try to find the user's worker (the one that has been handling their operations)
    if user:
        from SaveNLoad.models.operation_queue import OperationQueue
        
        # Find the worker that has handled the most operations for this user
        recent_operations = OperationQueue.objects.filter(
            user=user,
            client_worker__isnull=False
        ).exclude(client_worker=None).order_by('-created_at')[:50]
        
        if recent_operations.exists():
            # Count operations per worker
            worker_counts = {}
            for op in recent_operations:
                if op.client_worker and op.client_worker.is_online():
                    worker_id = op.client_worker.id
                    worker_counts[worker_id] = worker_counts.get(worker_id, 0) + 1
            
            if worker_counts:
                # Get the worker with the most operations
                most_common_worker_id = max(worker_counts.items(), key=lambda x: x[1])[0]
                try:
                    client_worker = ClientWorker.objects.get(id=most_common_worker_id, is_active=True)
                    if client_worker.is_online():
                        return client_worker, None
                except ClientWorker.DoesNotExist:
                    pass
    
    # No worker found - app requires workers to function
    return None, JsonResponse({
        'error': 'No client worker available',
        'requires_worker': True
    }, status=503)


def check_admin_or_error(user):
    """
    Check if user is admin, return error response if not
    Returns: error_response_or_none
    """
    if not user or not user.is_admin():
        return json_response_error('Unauthorized', status=403)
    return None


def check_worker_connected_or_redirect():
    """
    Check if client worker is connected, redirect if not
    Returns: redirect_response_or_none
    """
    if not ClientWorker.is_worker_connected():
        return redirect(reverse('SaveNLoad:worker_required'))
    return None


def redirect_if_logged_in(request):
    """
    Redirect user to appropriate dashboard if already logged in
    Returns: redirect_response_or_none
    """
    user = get_current_user(request)
    if user:
        if user.is_admin():
            return redirect(reverse('admin:dashboard'))
        else:
            return redirect(reverse('user:dashboard'))
    return None


def json_response_with_redirect(message, redirect_url):
    """
    Create JSON response with redirect header for AJAX requests
    """
    response = json_response_success(message=message)
    response['X-Redirect-URL'] = redirect_url
    return response


def json_response_field_errors(field_errors, general_errors=None, message=None):
    """
    Create JSON response with field errors (for form validation)
    """
    response = {
        'success': False,
        'field_errors': field_errors
    }
    if general_errors:
        response['errors'] = general_errors
    if message:
        response['message'] = message
    return JsonResponse(response, status=400)


def get_client_worker_by_id_or_error(client_id):
    """
    Get client worker by client_id or return error response
    Returns: (client_worker_object, error_response_or_none)
    """
    if not client_id:
        return None, json_response_error('client_id is required', status=400)
    
    try:
        worker = ClientWorker.objects.get(client_id=client_id)
        return worker, None
    except ClientWorker.DoesNotExist:
        return None, json_response_error('Client not registered', status=404)

