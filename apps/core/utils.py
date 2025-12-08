"""
Core utility functions used across the application.
"""
from datetime import datetime, timezone
from typing import Optional


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """
    Format datetime to: 2025-12-06 04:21:53.151+00
    
    Args:
        dt: Datetime object to format. If None, uses current UTC time.
        
    Returns:
        str: Formatted timestamp string with space separator, 3 decimal places, +00 timezone
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] + '+00'

