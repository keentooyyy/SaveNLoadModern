"""
String manipulation utilities
Common string operations used across the codebase
"""
import re


def safe_get_and_strip(data: dict, key: str, default: str = '') -> str:
    """
    Safely get value from dict and strip whitespace
    
    Used extensively in:
    - Request data parsing
    - Form data handling
    
    Args:
        data: Dictionary to get value from
        key: Key to look up
        default: Default value if key not found
        
    Returns:
        Stripped string value
    """
    return (data.get(key, default) or '').strip()


def case_insensitive_contains(text: str, search_terms: list) -> bool:
    """
    Check if text contains any of the search terms (case-insensitive)
    
    Used in:
    - Error message matching
    - Validation checks
    
    Args:
        text: Text to search in
        search_terms: List of terms to search for
        
    Returns:
        True if any term found, False otherwise
    """
    if not text:
        return False
    
    text_lower = text.lower()
    return any(term.lower() in text_lower for term in search_terms if term)


def normalize_to_lower(value: str) -> str:
    """
    Normalize string to lowercase (handles None)
    
    Used in:
    - Email comparisons
    - Case-insensitive checks
    
    Args:
        value: String to normalize
        
    Returns:
        Lowercase string or empty string if None
    """
    return (value or '').lower()


def emails_match(email1: str, email2: str) -> bool:
    """
    Compare two emails case-insensitively
    
    Used in:
    - PasswordResetOTP email validation
    - User email verification
    
    Args:
        email1: First email
        email2: Second email
        
    Returns:
        True if emails match (case-insensitive)
    """
    return normalize_to_lower(email1) == normalize_to_lower(email2)


def transform_path_error_message(error_message: str, operation_type: str) -> str:
    """
    Transform technical error messages to user-friendly format
    
    Used in:
    - Operation error handling
    - User-facing error messages
    
    Args:
        error_message: Original error message
        operation_type: Type of operation ('save', 'load', etc.)
        
    Returns:
        User-friendly error message
    """
    if not error_message:
        return error_message
    
    error_lower = error_message.lower()
    
    # Check for path-related errors
    path_errors = [
        'local save path does not exist',
        'local file not found',
        'path does not exist',
        'file not found'
    ]
    
    if any(err in error_lower for err in path_errors):
        if operation_type == 'save':
            return 'Oops! You don\'t have any save files to save. Maybe you haven\'t played the game yet, or the save location is incorrect.'
        elif operation_type == 'load':
            return 'Oops! You don\'t have any save files to load. Maybe you haven\'t saved this game yet.'
    
    return error_message


def check_database_table_exists(model_class):
    """
    Check if database table exists for a model
    
    Used in:
    - Management commands
    - Database initialization checks
    
    Args:
        model_class: Django model class
        
    Returns:
        (exists: bool, error_message: str or None)
    """
    from django.db import OperationalError, ProgrammingError
    
    try:
        model_class.objects.first()
        return True, None
    except (OperationalError, ProgrammingError) as e:
        error_msg = str(e).lower()
        if 'does not exist' in error_msg or 'relation' in error_msg:
            return False, 'Database tables do not exist. Please run migrations first.'
        else:
            # Re-raise if it's a different database error
            raise

