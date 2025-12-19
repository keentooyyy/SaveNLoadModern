"""
List and sorting utilities
Common patterns for sorting, filtering, and manipulating lists
"""


def sort_by_field(items: list, field: str, reverse: bool = False, case_insensitive: bool = False):
    """
    Sort list of dicts/objects by field
    
    Used in:
    - Game list sorting
    - Dashboard sorting
    
    Args:
        items: List of dicts or objects
        field: Field name to sort by
        reverse: Sort in reverse order
        case_insensitive: Convert to lowercase for comparison
        
    Returns:
        Sorted list
    """
    def get_value(item):
        if isinstance(item, dict):
            value = item.get(field)
        else:
            value = getattr(item, field, None)
        
        if case_insensitive and value:
            return str(value).lower()
        return value
    
    return sorted(items, key=get_value, reverse=reverse)


def sort_by_dict_lookup(items: list, lookup_dict: dict, key_func=None, reverse: bool = False):
    """
    Sort list by values from a lookup dictionary
    
    Used in:
    - Sorting games by last_played from separate dict
    - Any sorting that requires external lookup
    
    Args:
        items: List of items to sort
        lookup_dict: Dictionary to lookup values from
        key_func: Function to get key from item (default: item.id or item['id'])
        reverse: Sort in reverse order
        
    Returns:
        Sorted list
    """
    if key_func is None:
        def key_func(item):
            if isinstance(item, dict):
                return item.get('id')
            else:
                return getattr(item, 'id', None)
    
    return sorted(items, key=lambda x: lookup_dict.get(key_func(x)), reverse=reverse)


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

