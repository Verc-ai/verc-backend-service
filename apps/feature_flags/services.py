"""
Feature flag service for checking and caching feature flag status.
"""
import logging
from typing import Optional
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def is_feature_enabled(flag_key: str, default: bool = False) -> bool:
    """
    Check if a feature flag is enabled.

    This function checks feature flags with the following fallback chain:
    1. Redis cache (60-second TTL)
    2. Supabase database query
    3. Default value

    Args:
        flag_key: The feature flag key to check (e.g., 'pbx-monitor')
        default: Default value to return if flag not found or error occurs

    Returns:
        True if feature is enabled, False otherwise

    Example:
        >>> if is_feature_enabled('pbx-monitor', default=True):
        >>>     start_pbx_monitor()
    """

    # Step 1: Check Redis cache first (fast path)
    cache_key = f'feature_flag:{flag_key}'
    cached_value = cache.get(cache_key)

    if cached_value is not None:
        # Cache hit - return cached boolean value
        is_enabled = cached_value == 'enabled'
        logger.debug(
            f'[FEATURE-FLAG] Cache hit for {flag_key}: {is_enabled}'
        )
        return is_enabled

    # Step 2: Cache miss - query Supabase
    logger.debug(
        f'[FEATURE-FLAG] Cache miss for {flag_key}, querying Supabase...'
    )

    try:
        from apps.core.services.supabase import get_supabase_client

        supabase = get_supabase_client()
        if not supabase:
            logger.warning(
                f'[FEATURE-FLAG] Supabase not available for {flag_key}, '
                f'using default={default}'
            )
            return default

        # Query feature flags table
        result = supabase.table('feature_flags').select('enabled').eq('flag_key', flag_key).execute()

        if not result.data or len(result.data) == 0:
            # Flag not found in database - use default
            logger.info(
                f'[FEATURE-FLAG] Flag {flag_key} not found in database, '
                f'using default={default}'
            )
            # Cache the default value for 60 seconds to reduce DB load
            cache.set(cache_key, 'enabled' if default else 'disabled', 60)
            return default

        # Flag found - get enabled status
        flag_data = result.data[0]
        is_enabled = flag_data.get('enabled', default)

        # Cache the result for 60 seconds
        cache_value = 'enabled' if is_enabled else 'disabled'
        cache.set(cache_key, cache_value, 60)

        logger.info(
            f'[FEATURE-FLAG] Flag {flag_key} fetched from Supabase: {is_enabled} '
            f'(cached for 60s)'
        )

        return is_enabled

    except Exception as e:
        # Step 3: Error fallback - use default value
        logger.error(
            f'[FEATURE-FLAG] Error checking flag {flag_key}: {e}, '
            f'using default={default}',
            exc_info=True
        )
        return default


def invalidate_feature_flag_cache(flag_key: Optional[str] = None):
    """
    Invalidate feature flag cache.

    Args:
        flag_key: Specific flag to invalidate, or None to clear all flags

    Example:
        >>> # Clear specific flag
        >>> invalidate_feature_flag_cache('pbx-monitor')
        >>>
        >>> # Clear all feature flags
        >>> invalidate_feature_flag_cache()
    """
    if flag_key:
        # Clear specific flag
        cache_key = f'feature_flag:{flag_key}'
        cache.delete(cache_key)
        logger.info(f'[FEATURE-FLAG] Invalidated cache for {flag_key}')
    else:
        # Clear all feature flags (pattern-based deletion)
        # Note: This requires cache backend that supports pattern deletion
        # For Redis, we can use delete_pattern
        try:
            # Try pattern deletion if supported
            cache.delete_pattern('feature_flag:*')
            logger.info('[FEATURE-FLAG] Invalidated all feature flag caches')
        except AttributeError:
            # Fallback: Log warning if pattern deletion not supported
            logger.warning(
                '[FEATURE-FLAG] Cache backend does not support pattern deletion, '
                'individual flags must be invalidated manually'
            )
