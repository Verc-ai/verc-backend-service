"""
Redis caching helpers for analytics data.
"""
from typing import Optional, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

# Try to import redis, but make it optional
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - caching disabled")


def get_redis_client():
    """
    Get Redis client instance.
    
    Returns:
        Optional[redis.Redis]: Redis client or None if not available
    """
    if not REDIS_AVAILABLE:
        return None
    
    try:
        from django.conf import settings
        from channels_redis.core import connection
        
        # Use the same Redis connection as Channels
        # This reuses the connection pool configured in CHANNEL_LAYERS
        return connection.get_connection()
    except Exception as e:
        logger.warning(f"Failed to get Redis client: {e}")
        return None


def get_cached_scorecard(cache_key: str) -> Optional[Dict[str, Any]]:
    """
    Get cached scorecard data.
    
    Args:
        cache_key: Cache key string
        
    Returns:
        Optional[dict]: Cached data or None if not found
    """
    redis_client = get_redis_client()
    if not redis_client:
        return None
    
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Error reading from cache: {e}")
    
    return None


def cache_scorecard(cache_key: str, data: Dict[str, Any], ttl: int = 300):
    """
    Cache scorecard data.
    
    Args:
        cache_key: Cache key string
        data: Data to cache
        ttl: Time to live in seconds (default: 5 minutes)
    """
    redis_client = get_redis_client()
    if not redis_client:
        return
    
    try:
        redis_client.setex(
            cache_key,
            ttl,
            json.dumps(data)
        )
    except Exception as e:
        logger.warning(f"Error writing to cache: {e}")


def get_cached_trends(cache_key: str) -> Optional[Dict[str, Any]]:
    """
    Get cached trends data.
    
    Args:
        cache_key: Cache key string
        
    Returns:
        Optional[dict]: Cached data or None if not found
    """
    redis_client = get_redis_client()
    if not redis_client:
        return None
    
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Error reading from cache: {e}")
    
    return None


def cache_trends(cache_key: str, data: Dict[str, Any], ttl: int = 300):
    """
    Cache trends data.
    
    Args:
        cache_key: Cache key string
        data: Data to cache
        ttl: Time to live in seconds (default: 5 minutes)
    """
    redis_client = get_redis_client()
    if not redis_client:
        return
    
    try:
        redis_client.setex(
            cache_key,
            ttl,
            json.dumps(data)
        )
    except Exception as e:
        logger.warning(f"Error writing to cache: {e}")


def get_cached_health(cache_key: str) -> Optional[Dict[str, Any]]:
    """
    Get cached health metrics.
    
    Args:
        cache_key: Cache key string
        
    Returns:
        Optional[dict]: Cached data or None if not found
    """
    redis_client = get_redis_client()
    if not redis_client:
        return None
    
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Error reading from cache: {e}")
    
    return None


def cache_health(cache_key: str, data: Dict[str, Any], ttl: int = 300):
    """
    Cache health metrics.
    
    Args:
        cache_key: Cache key string
        data: Data to cache
        ttl: Time to live in seconds (default: 5 minutes)
    """
    redis_client = get_redis_client()
    if not redis_client:
        return
    
    try:
        redis_client.setex(
            cache_key,
            ttl,
            json.dumps(data)
        )
    except Exception as e:
        logger.warning(f"Error writing to cache: {e}")

