"""Export utilities for dashboard data

Functions for creating CSV and JSON export responses.
"""

import csv
import io
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Union

from flask import Response, make_response

from src.dashboard.utils.data import flatten_dict
from src.dashboard.utils.formatting import format_value_for_csv


def create_csv_response(data: Union[List[Dict], Dict], filename: str) -> Response:
    """Create CSV response from data

    Flattens nested dictionaries, formats values, and creates a Flask
    response with CSV content for file download.

    Args:
        data: List of dictionaries or single dictionary to export
        filename: Filename for download (e.g., "metrics_2025-01-25.csv")

    Returns:
        Flask response with CSV file attachment

    Examples:
        >>> data = [{"name": "John", "score": 95.5}, {"name": "Jane", "score": 87.2}]
        >>> response = create_csv_response(data, "scores.csv")
        >>> response.headers["Content-Type"]
        'text/csv; charset=utf-8'
    """
    # Ensure data is a list
    if isinstance(data, dict):
        data = [data]

    if not data:
        return make_response("No data to export", 404)

    # Flatten all dictionaries
    flattened_data = [flatten_dict(item) for item in data]

    # Get all unique keys
    all_keys: set[str] = set()
    for item in flattened_data:
        all_keys.update(item.keys())

    # Sort keys for consistent output
    fieldnames = sorted(all_keys)

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for item in flattened_data:
        # Format values
        formatted_item = {k: format_value_for_csv(v) for k, v in item.items()}
        writer.writerow(formatted_item)

    # Sanitize filename to prevent header injection and XSS
    # Remove any characters that aren't alphanumeric, dash, underscore, or dot
    safe_filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
    # Ensure filename isn't empty and doesn't start with a dot
    if not safe_filename or safe_filename.startswith("."):
        safe_filename = f"export_{safe_filename}"

    # Explicit validation: Verify no dangerous characters remain (for CodeQL)
    # This assertion helps static analyzers understand the value is safe
    if not re.match(r"^[a-zA-Z0-9._-]+$", safe_filename):
        # Fallback: use a completely safe default filename
        safe_filename = "export_data.csv"

    # Create response
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = f'attachment; filename="{safe_filename}"'
    response.headers["X-Content-Type-Options"] = "nosniff"  # Prevents MIME sniffing

    return response


def create_json_response(data: Any, filename: str) -> Response:
    """Create JSON response from data

    Serializes data to JSON with datetime handling and security headers.
    Includes XSS protection via ensure_ascii and header injection prevention.

    Args:
        data: Dictionary or list to export
        filename: Filename for download (e.g., "metrics_2025-01-25.json")

    Returns:
        Flask response with JSON file attachment

    Examples:
        >>> data = {"name": "John", "score": 95}
        >>> response = create_json_response(data, "metrics.json")
        >>> response.headers["Content-Type"]
        'application/json; charset=utf-8'
    """

    # Convert datetime and numpy objects to JSON-serializable types
    def json_serializer(obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        # Handle numpy types (numpy.int64, numpy.float64, etc.)
        if hasattr(obj, "item"):  # numpy types have .item() method
            return obj.item()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    # Use json.dumps with ensure_ascii=True for additional XSS protection
    # ensure_ascii escapes all non-ASCII characters, making it safe for any context
    json_str = json.dumps(data, indent=2, default=json_serializer, ensure_ascii=True)

    # Sanitize filename to prevent header injection and XSS
    # Remove any characters that aren't alphanumeric, dash, underscore, or dot
    safe_filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
    # Ensure filename isn't empty and doesn't start with a dot
    if not safe_filename or safe_filename.startswith("."):
        safe_filename = f"export_{safe_filename}"

    # Explicit validation: Verify no dangerous characters remain (for CodeQL)
    # This assertion helps static analyzers understand the value is safe
    if not re.match(r"^[a-zA-Z0-9._-]+$", safe_filename):
        # Fallback: use a completely safe default filename
        safe_filename = "export_data.json"

    # Create response with explicit JSON content type and charset
    # The filename is now guaranteed safe by regex validation above
    response = Response(
        json_str,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "X-Content-Type-Options": "nosniff",  # Prevents MIME sniffing
        },
    )

    return response
