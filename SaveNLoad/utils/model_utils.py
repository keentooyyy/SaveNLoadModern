"""
Model query utilities
Common model filtering and query operations used across the codebase
"""
from django.db import models


def filter_by_user_and_game(queryset_or_model, user, game):
    """
    Filter a queryset by user and game
    
    This utility function provides a consistent way to filter models
    that have both user and game ForeignKey fields. It works with
    both model classes and querysets.
    
    Used extensively in:
    - SaveFolder filtering
    - OperationQueue filtering
    - Any model that needs user+game filtering
    
    Args:
        queryset_or_model: Django model class or queryset to filter
        user: User instance to filter by
        game: Game instance to filter by
        
    Returns:
        Filtered queryset containing only records matching user and game
        
    Example:
        save_folders = filter_by_user_and_game(SaveFolder, user, game)
        save_folders = filter_by_user_and_game(SaveFolder.objects.all(), user, game)
    """
    # Handle both model class and queryset
    if isinstance(queryset_or_model, models.QuerySet):
        queryset = queryset_or_model
    else:
        # Assume it's a model class
        queryset = queryset_or_model.objects.all()
    
    # Filter by user and game
    return queryset.filter(user=user, game=game)

