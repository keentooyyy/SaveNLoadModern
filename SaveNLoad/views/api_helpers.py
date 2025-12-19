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


def get_client_worker_or_error(user, request=None):
    """
    Get client worker for a user or return error response
    Uses client_id from session - if not available or worker is offline, fails immediately
    Returns: (client_worker_object, error_response_or_none)
    
    Note: App requires workers to function - if user's worker is not available, operation fails
    """
    if not user:
        return None, json_response_error('User is required', status=400)
    
    # Get client_id from session (user's current machine)
    client_id = None
    if request and hasattr(request, 'session'):
        client_id = request.session.get('client_id')
    
    if not client_id:
        # No worker in session - app requires worker to function
        return None, JsonResponse({
            'error': 'No client worker available. Please ensure the client worker is running on your machine.',
            'requires_worker': True
        }, status=503)
    
    # Try to get the worker from session
    try:
        client_worker = ClientWorker.objects.get(client_id=client_id, is_active=True)
        if client_worker.is_online():
            return client_worker, None
        else:
            # Worker in session is offline - fail immediately
            return None, JsonResponse({
                'error': f'Client worker ({client_id}) is offline. Please ensure the client worker is running.',
                'requires_worker': True
            }, status=503)
    except ClientWorker.DoesNotExist:
        # client_id in session doesn't exist anymore - clear it and fail
        if request and hasattr(request, 'session'):
            request.session.pop('client_id', None)
        return None, JsonResponse({
            'error': 'Client worker not found. Please ensure the client worker is running on your machine.',
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

