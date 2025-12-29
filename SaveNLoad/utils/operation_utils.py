"""
Operation-related utilities
Common patterns for operation status checking and processing
"""
from SaveNLoad.models.operation_constants import OperationType
from SaveNLoad.services.redis_operation_service import OperationStatus


def is_operation_type(operation, operation_type: str) -> bool:
    """
    Check if operation is of specific type
    
    Used in:
    - Operation completion handling
    - Operation type checking
    
    Args:
        operation: OperationQueue instance or dict with 'operation_type'
        operation_type: Type to check ('save', 'load', 'delete', etc.)
        
    Returns:
        True if operation matches type
    """
    if hasattr(operation, 'operation_type'):
        return operation.operation_type == operation_type
    elif isinstance(operation, dict):
        return operation.get('operation_type') == operation_type
    return False


def is_game_deletion_operation(operation) -> bool:
    """
    Check if operation is a game deletion operation
    (DELETE operation without save_folder_number)
    
    Used in:
    - Game deletion completion checks
    
    Args:
        operation: OperationQueue instance or dict
        
    Returns:
        True if this is a game deletion operation
    """
    if not is_operation_type(operation, OperationType.DELETE):
        return False
    
    if hasattr(operation, 'save_folder_number'):
        return operation.save_folder_number is None
    elif isinstance(operation, dict):
        return operation.get('save_folder_number') is None
    
    return False


def is_save_folder_operation(operation) -> bool:
    """
    Check if operation is a save folder operation
    (DELETE operation with save_folder_number)
    
    Used in:
    - Save folder deletion handling
    
    Args:
        operation: OperationQueue instance or dict
    
    Returns:
        True if this is a save folder deletion operation
    """
    if not is_operation_type(operation, OperationType.DELETE):
        return False
    
    if hasattr(operation, 'save_folder_number'):
        return operation.save_folder_number is not None
    elif isinstance(operation, dict):
        return operation.get('save_folder_number') is not None
    
    return False


def is_user_deletion_operation(operation) -> bool:
    """
    Check if operation is a user deletion operation
    (DELETE operation with game=None and save_folder_number=None)
    
    Used in:
    - User deletion completion checks
    
    Args:
        operation: OperationQueue instance or dict
    
    Returns:
        True if this is a user deletion operation
    """
    if not is_operation_type(operation, OperationType.DELETE):
        return False
    
    # User deletion operations have game=None and save_folder_number=None
    if hasattr(operation, 'game'):
        game_is_none = operation.game is None
        save_folder_is_none = hasattr(operation, 'save_folder_number') and operation.save_folder_number is None
        return game_is_none and save_folder_is_none
    elif isinstance(operation, dict):
        return operation.get('game') is None and operation.get('save_folder_number') is None
    
    return False


def get_operations_by_status(operations_list, status: str):
    """
    Filter operations by status
    
    Used in:
    - Operation queue management
    - Status-based queries
    
    Args:
        operations_list: List of operation dicts
        status: Status to filter by
        
    Returns:
        Filtered list of operations
    """
    return [op for op in operations_list if op.get('status') == status]


def get_pending_or_in_progress_operations(operations_list):
    """
    Get operations that are pending or in progress
    
    Used in:
    - Game deletion completion checks
    - Operation status queries
    
    Args:
        operations_list: List of operation dicts
        
    Returns:
        Filtered list of operations
    """
    return [op for op in operations_list if op.get('status') in [OperationStatus.PENDING, OperationStatus.IN_PROGRESS]]


def check_all_operations_succeeded(operations_list) -> bool:
    """
    Check if all operations in list succeeded (status=COMPLETED)
    
    Used in:
    - Game deletion completion check
    
    Args:
        operations_list: List of operation dicts
        
    Returns:
        True if all operations are COMPLETED
    """
    return all(op.get('status') == OperationStatus.COMPLETED for op in operations_list)

