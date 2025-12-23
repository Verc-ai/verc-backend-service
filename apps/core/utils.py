"""
Core utility functions used across the application.
"""
from datetime import datetime, timezone
from typing import Optional, Callable, Any, TypeVar
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


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


def retry_on_exception(
    max_attempts: int = 3,
    backoff_base: float = 0.5,
    exceptions: tuple = (Exception,)
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Retry decorator with exponential backoff for handling transient failures.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        backoff_base: Base delay in seconds for exponential backoff (default: 0.5s)
                      Delays will be: 0.5s, 1s, 2s for default settings
        exceptions: Tuple of exception types to catch and retry (default: all exceptions)

    Returns:
        Decorated function that retries on specified exceptions

    Example:
        @retry_on_exception(max_attempts=3, backoff_base=0.5)
        def call_api():
            return api.fetch_data()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    elapsed = time.time() - start_time

                    if attempt > 1:
                        logger.info(
                            f"✅ {func.__name__} succeeded on attempt {attempt} "
                            f"(took {elapsed:.2f}s)"
                        )

                    return result

                except exceptions as e:
                    last_exception = e
                    elapsed = time.time() - start_time

                    if attempt < max_attempts:
                        delay = backoff_base * (2 ** (attempt - 1))
                        logger.warning(
                            f"⚠️ {func.__name__} failed on attempt {attempt}/{max_attempts} "
                            f"(took {elapsed:.2f}s): {str(e)}. "
                            f"Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"❌ {func.__name__} failed after {max_attempts} attempts "
                            f"(last attempt took {elapsed:.2f}s): {str(e)}"
                        )

            # All attempts failed, raise the last exception
            raise last_exception

        return wrapper
    return decorator

