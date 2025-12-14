"""
Raw SQL queries and database access for analytics.
Uses Supabase Postgres for data retrieval.
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from apps.core.services.supabase import get_supabase_client
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_period_dates(period: str, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> Tuple[datetime, datetime]:
    """
    Get start and end dates for a given period.
    
    Args:
        period: Time period string (e.g., "last_7_days", "last_30_days", "custom")
        start_date_str: Optional ISO date string for custom range
        end_date_str: Optional ISO date string for custom range
        
    Returns:
        tuple: (start_date, end_date) as timezone-aware datetime objects (UTC)
    """
    # Handle custom date range - check if dates are provided (even if period isn't exactly "custom")
    if start_date_str and end_date_str:
        try:
            # Handle both date-only strings (YYYY-MM-DD) and full ISO strings
            # Date inputs send YYYY-MM-DD format
            if len(start_date_str) == 10 and start_date_str.count('-') == 2:
                # Date-only format: set to start of day
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            else:
                # Full ISO string format
                start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
                if start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=timezone.utc)
            
            if len(end_date_str) == 10 and end_date_str.count('-') == 2:
                # Date-only format: set to end of day (23:59:59)
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59, tzinfo=timezone.utc
                )
            else:
                # Full ISO string format
                end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                if end_date.tzinfo is None:
                    end_date = end_date.replace(tzinfo=timezone.utc)
            
            logger.info(f"Parsed custom date range (period={period}): {start_date} to {end_date}")
            return start_date, end_date
        except Exception as e:
            logger.warning(f"Error parsing custom dates: {e}, falling back to default", exc_info=True)
    
    # Use timezone-aware UTC datetime
    # For preset periods, use full calendar days (start of start day to end of end day)
    # This ensures consistent behavior with custom date ranges
    end_date = datetime.now(timezone.utc)
    
    if period == "last_7_days":
        start_date = (end_date - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "last_30_days":
        start_date = (end_date - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "last_90_days":
        start_date = (end_date - timedelta(days=90)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == "last_year":
        start_date = (end_date - timedelta(days=365)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        # Default to last 30 days
        start_date = (end_date - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return start_date, end_date


def get_sessions_count(user_id: Optional[str], period: str, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> int:
    """
    Get total number of sessions in the given period.
    
    Args:
        user_id: User ID for tenant filtering (optional)
        period: Time period string
        
    Returns:
        int: Total number of sessions
    """
    supabase = get_supabase_client()
    if not supabase:
        logger.warning("Supabase client not available")
        return 0
    
    try:
        start_date, end_date = get_period_dates(period, start_date_str, end_date_str)
        config = settings.APP_SETTINGS.supabase
        
        # Format dates as ISO strings for Supabase (without microseconds)
        query_start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        query_end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        logger.info(f"Fetching sessions count for period {period}: {query_start_str} to {query_end_str}")
        
        query = (
            supabase.table(config.sessions_table)
            .select("id", count="exact")
            .gte("created_at", query_start_str)
            .lte("created_at", query_end_str)
        )
        
        # TODO: Add tenant filtering when user_id is provided
        # This requires understanding the tenant/user relationship in your schema
        
        response = query.execute()
        count = response.count if hasattr(response, 'count') else len(response.data)
        logger.info(f"Found {count} sessions for period {period}")
        return count
    except Exception as e:
        logger.error(f"Error fetching sessions count: {e}", exc_info=True)
        return 0


def get_acceptance_rate(user_id: Optional[str], period: str, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> float:
    """
    Calculate acceptance rate (percentage of accepted calls).
    
    Args:
        user_id: User ID for tenant filtering (optional)
        period: Time period string
        
    Returns:
        float: Acceptance rate as a decimal (0.0 to 1.0)
    """
    supabase = get_supabase_client()
    if not supabase:
        logger.warning("Supabase client not available")
        return 0.0
    
    try:
        start_date, end_date = get_period_dates(period, start_date_str, end_date_str)
        config = settings.APP_SETTINGS.supabase
        
        # Format dates as ISO strings for Supabase (without microseconds)
        query_start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        query_end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        logger.info(f"Fetching acceptance rate for period {period}: {query_start_str} to {query_end_str}")
        
        # Fetch sessions with metadata that might contain acceptance status
        # This is a placeholder - adjust based on your actual schema
        query = (
            supabase.table(config.sessions_table)
            .select("id, metadata")
            .gte("created_at", query_start_str)
            .lte("created_at", query_end_str)
        )
        
        response = query.execute()
        logger.info(f"Found {len(response.data)} sessions for acceptance rate calculation")
        
        if not response.data:
            return 0.0
        
        total = len(response.data)
        accepted = 0
        
        # Check metadata for acceptance status
        # Adjust this logic based on your actual data structure
        for session in response.data:
            metadata = session.get("metadata", {})
            if isinstance(metadata, dict):
                # Check various possible fields for acceptance
                if metadata.get("accepted") or metadata.get("status") == "accepted":
                    accepted += 1
        
        return accepted / total if total > 0 else 0.0
    except Exception as e:
        logger.error(f"Error calculating acceptance rate: {e}", exc_info=True)
        return 0.0


def get_avg_handle_time(user_id: Optional[str], period: str, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> float:
    """
    Calculate average handle time in seconds.
    
    Args:
        user_id: User ID for tenant filtering (optional)
        period: Time period string
        
    Returns:
        float: Average handle time in seconds
    """
    supabase = get_supabase_client()
    if not supabase:
        logger.warning("Supabase client not available")
        return 0.0
    
    try:
        start_date, end_date = get_period_dates(period, start_date_str, end_date_str)
        config = settings.APP_SETTINGS.supabase
        
        # Format dates as ISO strings for Supabase (without microseconds)
        query_start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        query_end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        logger.info(f"Fetching avg handle time for period {period}: {query_start_str} to {query_end_str}")
        
        # Use last_event_received_at instead of last_event_at (matches actual schema)
        query = (
            supabase.table(config.sessions_table)
            .select("created_at, last_event_received_at")
            .gte("created_at", query_start_str)
            .lte("created_at", query_end_str)
        )
        
        response = query.execute()
        logger.info(f"Found {len(response.data)} sessions for handle time calculation")
        
        if not response.data:
            return 0.0
        
        total_duration = 0
        count = 0
        
        for session in response.data:
            created_at = session.get("created_at")
            last_event_at = session.get("last_event_received_at") or created_at
            
            if created_at and last_event_at:
                try:
                    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    last_event = datetime.fromisoformat(last_event_at.replace("Z", "+00:00"))
                    duration = (last_event - created).total_seconds()
                    if duration > 0:
                        total_duration += duration
                        count += 1
                except Exception as e:
                    logger.warning(f"Error parsing dates: {e}")
                    continue
        
        return total_duration / count if count > 0 else 0.0
    except Exception as e:
        logger.error(f"Error calculating avg handle time: {e}", exc_info=True)
        return 0.0


def get_daily_metrics(user_id: Optional[str], period: str, metric: str, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> Dict[str, List]:
    """
    Get daily aggregated metrics for trend visualization.
    
    Args:
        user_id: User ID for tenant filtering (optional)
        period: Time period string
        metric: Metric name (e.g., "acceptance_rate", "total_calls")
        
    Returns:
        dict: {"x": [dates], "y": [values]}
    """
    supabase = get_supabase_client()
    if not supabase:
        logger.warning("Supabase client not available")
        return {"x": [], "y": []}
    
    try:
        start_date, end_date = get_period_dates(period, start_date_str, end_date_str)
        config = settings.APP_SETTINGS.supabase
        
        # Format dates as ISO strings for Supabase (without microseconds)
        query_start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        query_end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        logger.info(f"Fetching daily metrics for {metric}, period {period}: {query_start_str} to {query_end_str}")
        
        # CRITICAL FIX: Make ONE query instead of one per day!
        # Fetch all data in the date range in a single query
        query = (
            supabase.table(config.sessions_table)
            .select("created_at, metadata")
            .gte("created_at", query_start_str)
            .lte("created_at", query_end_str)
        )
        
        response = query.execute()
        all_sessions = response.data
        logger.info(f"Fetched {len(all_sessions)} sessions in single query for {metric}")
        
        # FIX 7: Downsample for long periods to reduce payload size
        # For periods > 30 days, use weekly aggregation instead of daily
        days_in_period = (end_date - start_date).days
        aggregation_interval = 7 if days_in_period > 30 else 1  # Weekly if > 30 days, daily otherwise
        
        # Simple approach: Group sessions by date string (YYYY-MM-DD)
        # This avoids all timezone complexity
        date_groups = defaultdict(list)
        
        for session in all_sessions:
            created_at_str = session.get("created_at")
            if not created_at_str:
                continue
                
            try:
                # Extract just the date part (YYYY-MM-DD) from ISO string
                # Supabase returns: "2025-12-13T21:10:36.123+00:00" or "2025-12-13T21:10:36Z"
                date_part = created_at_str.split("T")[0]  # Get "2025-12-13"
                date_groups[date_part].append(session)
            except Exception as e:
                logger.warning(f"Error extracting date from {created_at_str}: {e}")
                continue
        
        logger.info(f"Grouped {len(all_sessions)} sessions into {len(date_groups)} date groups")
        
        # Generate date range and aggregate values
        dates = []
        values = []
        
        # Generate all dates in the range
        # Normalize start_date to beginning of day
        current = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Normalize end_date to beginning of its day for the loop
        # (we'll include all sessions from that day since we query up to end_date which includes the full day)
        end_date_only = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        while current <= end_date_only:
            date_str = current.strftime("%Y-%m-%d")
            
            # For weekly aggregation, only include dates at interval boundaries
            if aggregation_interval == 1 or (current - start_date.replace(hour=0, minute=0, second=0, microsecond=0)).days % aggregation_interval == 0:
                # Get sessions for this date
                sessions_for_date = date_groups.get(date_str, [])
                
                if metric == "total_calls":
                    values.append(len(sessions_for_date))
                elif metric == "acceptance_rate":
                    accepted = sum(
                        1 for s in sessions_for_date
                        if isinstance(s.get("metadata", {}), dict) and
                        (s.get("metadata", {}).get("accepted") or
                         s.get("metadata", {}).get("status") == "accepted")
                    )
                    rate = accepted / len(sessions_for_date) if sessions_for_date else 0.0
                    values.append(rate)
                else:
                    values.append(0)
                
                dates.append(date_str)
            
            current += timedelta(days=1)
        
        # FIX 7: Limit to max 60 points to keep payloads small
        if len(dates) > 60:
            # Downsample by taking every Nth point
            step = len(dates) // 60
            dates = dates[::step]
            values = values[::step]
        
        logger.info(f"Returning {len(dates)} data points for {metric}, total values sum: {sum(values)}")
        if len(dates) == 0:
            logger.warning(f"No dates generated for {metric} - check date range logic")
        return {"x": dates, "y": values}
    except Exception as e:
        logger.error(f"Error fetching daily metrics: {e}", exc_info=True)
        return {"x": [], "y": []}


def get_call_intents(user_id: Optional[str], period: str, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> Dict[str, int]:
    """
    Get aggregated call intents count.
    
    Args:
        user_id: User ID for tenant filtering (optional)
        period: Time period string
        
    Returns:
        dict: {intent_name: count}
    """
    supabase = get_supabase_client()
    if not supabase:
        logger.warning("Supabase client not available")
        return {}
    
    try:
        start_date, end_date = get_period_dates(period, start_date_str, end_date_str)
        config = settings.APP_SETTINGS.supabase
        
        # Format dates as ISO strings for Supabase (without microseconds)
        query_start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        query_end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        logger.info(f"Fetching call intents for period {period}: {query_start_str} to {query_end_str}")
        
        query = (
            supabase.table(config.sessions_table)
            .select("call_scorecard_data")
            .gte("created_at", query_start_str)
            .lte("created_at", query_end_str)
            .not_.is_("call_scorecard_data", "null")
        )
        
        response = query.execute()
        logger.info(f"Found {len(response.data)} sessions with scorecard data for intents")
        
        intent_counts = {}
        
        for session in response.data:
            scorecard_data = session.get("call_scorecard_data", {})
            if isinstance(scorecard_data, dict):
                detected_intents = scorecard_data.get("detected_intents", [])
                if isinstance(detected_intents, list):
                    for intent in detected_intents:
                        if isinstance(intent, str):
                            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        return intent_counts
    except Exception as e:
        logger.error(f"Error fetching call intents: {e}", exc_info=True)
        return {}


def get_sentiment_distribution(user_id: Optional[str], period: str, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> Dict[str, int]:
    """
    Get sentiment distribution (positive, neutral, negative).
    
    Args:
        user_id: User ID for tenant filtering (optional)
        period: Time period string
        
    Returns:
        dict: {"positive": count, "neutral": count, "negative": count}
    """
    supabase = get_supabase_client()
    if not supabase:
        logger.warning("Supabase client not available")
        return {"positive": 0, "neutral": 0, "negative": 0}
    
    try:
        start_date, end_date = get_period_dates(period, start_date_str, end_date_str)
        config = settings.APP_SETTINGS.supabase
        
        # Format dates as ISO strings for Supabase (without microseconds)
        query_start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        query_end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        logger.info(f"Fetching sentiment distribution for period {period}: {query_start_str} to {query_end_str}")
        
        query = (
            supabase.table(config.sessions_table)
            .select("call_scorecard_data")
            .gte("created_at", query_start_str)
            .lte("created_at", query_end_str)
            .not_.is_("call_scorecard_data", "null")
        )
        
        response = query.execute()
        logger.info(f"Found {len(response.data)} sessions with scorecard data for sentiment")
        
        positive_count = 0
        neutral_count = 0
        negative_count = 0
        
        for session in response.data:
            scorecard_data = session.get("call_scorecard_data", {})
            if isinstance(scorecard_data, dict):
                transcript_sentiments = scorecard_data.get("transcript_sentiments", [])
                if isinstance(transcript_sentiments, list):
                    for sentiment_item in transcript_sentiments:
                        if isinstance(sentiment_item, dict):
                            score = sentiment_item.get("sentiment_score", 50)
                            if score >= 60:
                                positive_count += 1
                            elif score >= 40:
                                neutral_count += 1
                            else:
                                negative_count += 1
        
        return {
            "positive": positive_count,
            "neutral": neutral_count,
            "negative": negative_count,
        }
    except Exception as e:
        logger.error(f"Error fetching sentiment distribution: {e}", exc_info=True)
        return {"positive": 0, "neutral": 0, "negative": 0}

