"""
Common helper functions for API endpoints
"""
from django.http import JsonResponse
from SaveNLoad.models import Game
from SaveNLoad.models.client_worker import ClientWorker
from SaveNLoad.models.operation_queue import OperationQueue, OperationType
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


def get_client_worker_or_error(client_id=None):
    """
    Get available client worker or return error response
    Returns: (client_worker_object, error_response_or_none)
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
    else:
        # Get any available worker (optimized - single query)
        timeout_threshold = timezone.now() - timedelta(seconds=30)
        client_worker = ClientWorker.objects.filter(
            is_active=True,
            last_heartbeat__gte=timeout_threshold
        ).order_by('-last_heartbeat').first()
        
        if not client_worker:
            return None, JsonResponse({
                'error': 'No client worker available',
                'requires_worker': True
            }, status=503)
        
        return client_worker, None


def check_admin_or_error(user):
    """
    Check if user is admin, return error response if not
    Returns: error_response_or_none
    """
    if not user or not user.is_admin():
        return json_response_error('Unauthorized', status=403)
    return None

