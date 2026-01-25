"""Data transformation utilities for dashboard

Pure data manipulation functions with minimal dependencies.
"""

from typing import Any, Dict, List, Tuple


def flatten_dict(d: Dict, parent_key: str = "", sep: str = ".") -> Dict:
    """Flatten nested dictionary with dot notation

    Recursively flattens a nested dictionary structure into a single-level
    dictionary with keys joined by a separator.

    Args:
        d: Dictionary to flatten
        parent_key: Parent key for recursion (internal use)
        sep: Separator for nested keys (default: ".")

    Returns:
        Flattened dictionary with dot-notation keys

    Examples:
        >>> flatten_dict({"a": 1, "b": {"c": 2, "d": 3}})
        {'a': 1, 'b.c': 2, 'b.d': 3}
        >>> flatten_dict({"x": {"y": {"z": 1}}})
        {'x.y.z': 1}
        >>> flatten_dict({"a": [1, 2, 3]})
        {'a': '1, 2, 3'}
    """
    items: List[Tuple[str, Any]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # Convert lists to comma-separated strings
            items.append((new_key, ", ".join(str(x) for x in v)))
        else:
            items.append((new_key, v))
    return dict(items)
