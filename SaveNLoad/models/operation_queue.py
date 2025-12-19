"""
Operation Queue model for queuing save/load operations for client workers
"""
from django.db import models
from django.utils import timezone
from SaveNLoad.models.user import SimpleUsers
from SaveNLoad.models.game import Game
from SaveNLoad.models.client_worker import ClientWorker


class OperationStatus:
    """Operation status constants"""
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    FAILED = 'failed'
    
    CHOICES = [
        (PENDING, 'Pending'),
        (IN_PROGRESS, 'In Progress'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
    ]


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


class OperationQueue(models.Model):
    """Queue of operations waiting to be processed by client workers"""
    
    operation_type = models.CharField(max_length=30, choices=OperationType.CHOICES)
    status = models.CharField(max_length=20, choices=OperationStatus.CHOICES, default=OperationStatus.PENDING)
    user = models.ForeignKey(SimpleUsers, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    client_worker = models.ForeignKey(ClientWorker, on_delete=models.SET_NULL, null=True, blank=True,
                                     help_text="Client worker assigned to this operation")
    local_save_path = models.CharField(max_length=500, help_text="Local save file path")
    save_folder_number = models.IntegerField(null=True, blank=True, help_text="Optional save folder number")
    smb_path = models.CharField(max_length=500, null=True, blank=True, help_text="Full SMB path for the save folder (Windows format with backslashes)")
    result_data = models.JSONField(null=True, blank=True, help_text="Operation result data")
    error_message = models.TextField(null=True, blank=True, help_text="Error message if operation failed")
    progress_current = models.IntegerField(default=0, help_text="Current progress count (e.g., files processed)")
    progress_total = models.IntegerField(default=0, help_text="Total items to process")
    progress_message = models.CharField(max_length=200, null=True, blank=True, help_text="Current progress message")
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'operation_queue'
        verbose_name = 'Operation Queue'
        verbose_name_plural = 'Operation Queue'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.operation_type.upper()} - {self.game.name} ({self.status})"
    
    def assign_to_worker(self, worker: ClientWorker):
        """Assign this operation to a client worker"""
        self.client_worker = worker
        self.status = OperationStatus.IN_PROGRESS
        self.started_at = timezone.now()
        self.save()
    
    def mark_completed(self, result_data=None):
        """Mark operation as completed"""
        self.status = OperationStatus.COMPLETED
        self.completed_at = timezone.now()
        if result_data:
            self.result_data = result_data
        self.save()
    
    def mark_failed(self, error_message):
        """Mark operation as failed"""
        self.status = OperationStatus.FAILED
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save()
    
    @classmethod
    def get_pending_operations_for_worker(cls, client_worker: ClientWorker):
        """Get pending operations for a specific client worker"""
        return cls.objects.filter(
            client_worker=client_worker,
            status=OperationStatus.PENDING
        ).order_by('created_at')
    
    @classmethod
    def create_operation(cls, operation_type: str, user: SimpleUsers, game: Game, 
                        local_save_path: str, save_folder_number=None, smb_path=None, client_worker=None):
        """
        Create a new operation in the queue
        
        Args:
            operation_type: Type of operation (save, load, delete, etc.)
            user: User who owns the operation
            game: Game associated with the operation
            local_save_path: Local file path
            save_folder_number: Optional save folder number
            smb_path: Remote FTP path
            client_worker: ClientWorker instance (REQUIRED - must be provided to avoid collisions)
        
        Raises:
            ValueError: If client_worker is not provided
        """
        if client_worker is None:
            raise ValueError("client_worker is required - all operations must be assigned to a worker to prevent collisions")
        
        operation = cls.objects.create(
            operation_type=operation_type,
            user=user,
            game=game,
            local_save_path=local_save_path,
            save_folder_number=save_folder_number,
            smb_path=smb_path,
            client_worker=client_worker,
            status=OperationStatus.PENDING
        )
        return operation

