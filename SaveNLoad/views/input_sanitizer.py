"""
Input sanitization utilities to prevent XSS and SQL injection attacks
"""
import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.html import escape


def sanitize_username(username):
    """
    Sanitize username input to prevent XSS and injection attacks.
    Allows only alphanumeric characters, underscores, and hyphens.
    """
    if not username:
        return None
    
    # Strip whitespace
    username = username.strip()
    
    # Remove any HTML tags
    username = re.sub(r'<[^>]+>', '', username)
    
    # Only allow alphanumeric, underscore, and hyphen
    username = re.sub(r'[^a-zA-Z0-9_-]', '', username)
    
    # Limit length
    if len(username) > 150:
        username = username[:150]
    
    return username


def sanitize_email(email):
    """
    Sanitize email input to prevent XSS attacks.
    Validates email format and escapes special characters.
    """
    if not email:
        return None
    
    # Strip whitespace
    email = email.strip()
    
    # Remove any HTML tags
    email = re.sub(r'<[^>]+>', '', email)
    
    # Validate email format
    try:
        validate_email(email)
    except ValidationError:
        return None
    
    # Limit length
    if len(email) > 254:
        email = email[:254]
    
    return email.lower()  # Normalize to lowercase


def sanitize_string(text, max_length=None):
    """
    Sanitize general string input to prevent XSS attacks.
    Escapes HTML special characters.
    """
    if not text:
        return None
    
    # Strip whitespace
    text = text.strip()
    
    # Remove any HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Escape HTML special characters
    text = escape(text)
    
    # Limit length if specified
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text


def validate_username_format(username):
    """
    Validate username format - alphanumeric, underscore, hyphen only.
    Length between 3 and 150 characters.
    """
    if not username:
        return False
    
    if len(username) < 3 or len(username) > 150:
        return False
    
    # Only alphanumeric, underscore, and hyphen allowed
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False
    
    return True


def validate_password_strength(password):
    """
    Validate password strength.
    Returns (is_valid, error_message)
    """
    if not password:
        return False, 'Password is required.'
    
    if len(password) < 8:
        return False, 'Password must be at least 8 characters long.'
    
    if len(password) > 128:
        return False, 'Password is too long (maximum 128 characters).'
    
    return True, None


def sanitize_search_query(query, max_length=200):
    """
    Sanitize search query input to prevent XSS and injection attacks.
    Removes HTML tags and dangerous characters, but preserves search functionality.
    Does NOT escape HTML (since it's used in database queries, not HTML output).
    
    Args:
        query: Search query string
        max_length: Maximum length (default: 200)
        
    Returns:
        Sanitized query string or None if invalid
    """
    if not query:
        return None
    
    # Strip whitespace
    query = query.strip()
    
    if not query:
        return None
    
    # Remove any HTML tags
    query = re.sub(r'<[^>]+>', '', query)
    
    # Remove null bytes (dangerous)
    query = query.replace('\x00', '')
    
    # Limit length
    if len(query) > max_length:
        query = query[:max_length]
    
    return query
