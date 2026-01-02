"""
Operation type and status constants
Moved from operation_queue model to support Redis-based operations
"""

class OperationType:
    """
    Operation type constants used across worker and server.

    Args:
        None

    Returns:
        None
    """
    SAVE = 'save'
    LOAD = 'load'
    LIST = 'list'
    DELETE = 'delete'
    BACKUP = 'backup'
    OPEN_FOLDER = 'open_folder'
    
    # Keep choice tuples in sync with the constants above.
    CHOICES = [
        (SAVE, 'Save'),
        (LOAD, 'Load'),
        (LIST, 'List'),
        (DELETE, 'Delete'),
        (BACKUP, 'Backup'),
        (OPEN_FOLDER, 'Open Folder'),
    ]

