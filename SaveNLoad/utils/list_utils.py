"""
List and sorting utilities
Common patterns for sorting, filtering, and manipulating lists
"""


def sort_by_field(items: list, field: str, reverse: bool = False, case_insensitive: bool = False):
    """
    Sort list of dicts/objects by field with stable secondary sort by name
    
    Used in:
    - Game list sorting
    - Dashboard sorting
    
    Args:
        items: List of dicts or objects
        field: Field name to sort by
        reverse: Sort in reverse order
        case_insensitive: Convert to lowercase for comparison
        
    Returns:
        Sorted list (stable sort - items with equal primary values maintain consistent order)
    """
    def get_sort_key(item):
        # Primary sort value
        if isinstance(item, dict):
            primary_value = item.get(field)
            # Use title/name as secondary sort for stability (prefer 'title', fallback to 'name')
            secondary_value = item.get('title') or item.get('name', '')
        else:
            primary_value = getattr(item, field, None)
            # Use title/name as secondary sort for stability (prefer 'title', fallback to 'name')
            secondary_value = getattr(item, 'title', None) or getattr(item, 'name', '')
        
        # Handle case insensitive comparison
        if case_insensitive:
            if primary_value:
                primary_value = str(primary_value).lower()
            if secondary_value:
                secondary_value = str(secondary_value).lower()
        
        # Return tuple for multi-key sorting: (primary, secondary)
        # This ensures stable sorting when primary values are equal
        return (primary_value, secondary_value)
    
    return sorted(items, key=get_sort_key, reverse=reverse)


def sort_by_dict_lookup(items: list, lookup_dict: dict, key_func=None, reverse: bool = False):
    """
    Sort list by values from a lookup dictionary with stable secondary sort by name
    
    Used in:
    - Sorting games by last_played from separate dict
    - Any sorting that requires external lookup
    
    Args:
        items: List of items to sort
        lookup_dict: Dictionary to lookup values from
        key_func: Function to get key from item (default: item.id or item['id'])
        reverse: Sort in reverse order
        
    Returns:
        Sorted list (stable sort - items with equal lookup values maintain consistent order)
    """
    if key_func is None:
        def key_func(item):
            if isinstance(item, dict):
                return item.get('id')
            else:
                return getattr(item, 'id', None)
    
    # Use tuple for multi-key sorting: (lookup_value, name)
    # This ensures stable sorting when lookup values are equal
    def get_sort_key(item):
        lookup_value = lookup_dict.get(key_func(item))
        # Use title/name as secondary sort for stability (prefer 'title', fallback to 'name')
        if isinstance(item, dict):
            secondary_value = item.get('title') or item.get('name', '')
        else:
            secondary_value = getattr(item, 'title', None) or getattr(item, 'name', '')
        # Convert to lowercase for consistent comparison
        if secondary_value:
            secondary_value = str(secondary_value).lower()
        return (lookup_value, secondary_value)
    
    return sorted(items, key=get_sort_key, reverse=reverse)


def filter_none_values(items: list, field: str = None):
    """
    Filter out items where field is None
    
    Used in:
    - Filtering games without last_played
    - Removing None values from lists
    
    Args:
        items: List of dicts or objects
        field: Field name to check (if None, filters items that are None)
        
    Returns:
        Filtered list
    """
    if field is None:
        return [item for item in items if item is not None]
    
    return [item for item in items if _get_field_value(item, field) is not None]


def _get_field_value(item, field: str):
    """Helper to get field value from dict or object"""
    if isinstance(item, dict):
        return item.get(field)
    else:
        return getattr(item, field, None)

