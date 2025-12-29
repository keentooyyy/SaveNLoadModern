"""
Operation type and status constants
Moved from operation_queue model to support Redis-based operations
"""

class OperationType:
    """Operation type constants"""
    SAVE = 'save'
    LOAD = 'load'
    LIST = 'list'
    DELETE = 'delete'
    BACKUP = 'backup'
    OPEN_FOLDER = 'open_folder'
    
    CHOICES = [
        (SAVE, 'Save'),
        (LOAD, 'Load'),
        (LIST, 'List'),
        (DELETE, 'Delete'),
        (BACKUP, 'Backup'),
        (OPEN_FOLDER, 'Open Folder'),
    ]

