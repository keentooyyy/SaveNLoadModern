"""
Environment variable utilities
Common patterns for getting and validating environment variables
"""
import os


def get_env_or_error(var_name: str, error_message: str = None) -> str:
    """
    Get environment variable or raise error with helpful message
    
    Used in:
    - Management commands
    - Configuration checks
    
    Args:
        var_name: Environment variable name
        error_message: Custom error message (defaults to "{var_name} environment variable is not set")
        
    Returns:
        Environment variable value
        
    Raises:
        ValueError: If environment variable is not set
    """
    value = os.getenv(var_name)
    if not value:
        if error_message:
            raise ValueError(error_message)
        else:
            raise ValueError(f"{var_name} environment variable is not set")
    return value


def get_env_with_default(var_name: str, default: str = '') -> str:
    """
    Get environment variable with default value
    
    Used in:
    - Optional configuration
    - Settings with fallbacks
    
    Args:
        var_name: Environment variable name
        default: Default value if not set
        
    Returns:
        Environment variable value or default
    """
    return os.getenv(var_name, default)

