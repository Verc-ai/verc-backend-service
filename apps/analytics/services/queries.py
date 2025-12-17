"""
Raw SQL queries and database access for analytics.
Uses Supabase Postgres for data retrieval.
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from apps.core.services.supabase import get_supabase_client
from apps.ai.constants import SCORECARD_THRESHOLDS
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
            .gte("call_start_time", query_start_str)
            .lte("call_start_time", query_end_str)
            .eq("IS_FALSE", False)  # Only include valid calls (IS_FALSE=FALSE)
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
            .gte("call_start_time", query_start_str)
            .lte("call_start_time", query_end_str)
            .eq("IS_FALSE", False)  # Only include valid calls (IS_FALSE=FALSE)
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
            .gte("call_start_time", query_start_str)
            .lte("call_start_time", query_end_str)
            .eq("IS_FALSE", False)  # Only include valid calls (IS_FALSE=FALSE)
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
        # Use call_start_time for accurate date aggregation (not created_at which is ingestion time)
        query = (
            supabase.table(config.sessions_table)
            .select("call_start_time, metadata")
            .gte("call_start_time", query_start_str)
            .lte("call_start_time", query_end_str)
            .eq("IS_FALSE", False)  # Only include valid calls (IS_FALSE=FALSE)
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
            call_start_time_str = session.get("call_start_time")
            if not call_start_time_str:
                continue

            try:
                # Extract just the date part (YYYY-MM-DD) from ISO string
                # Supabase returns: "2025-12-13T21:10:36.123+00:00" or "2025-12-13T21:10:36Z"
                date_part = call_start_time_str.split("T")[0]  # Get "2025-12-13"
                date_groups[date_part].append(session)
            except Exception as e:
                logger.warning(f"Error extracting date from {call_start_time_str}: {e}")
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
            .select("call_scorecard")
            .gte("call_start_time", query_start_str)
            .lte("call_start_time", query_end_str)
            .eq("IS_FALSE", False)  # Only include valid calls (IS_FALSE=FALSE)
            .not_.is_("call_scorecard", "null")
        )

        response = query.execute()
        logger.info(f"Found {len(response.data)} sessions with scorecard data for intents")

        intent_counts = {}

        for session in response.data:
            scorecard_data = session.get("call_scorecard", {})
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
    Get sentiment distribution with shift tracking.

    Returns 7 mutually exclusive categories:
    - positive: Calls that started and stayed positive
    - neutral: Calls that started and stayed neutral
    - negative: Calls that started and stayed negative
    - negative_to_positive: Calls that improved from negative to positive
    - neutral_to_positive: Calls that improved from neutral to positive
    - neutral_to_negative: Calls that declined from neutral to negative
    - positive_to_negative: Calls that declined from positive to negative

    Args:
        user_id: User ID for tenant filtering (optional)
        period: Time period string

    Returns:
        dict: Count for each of the 7 sentiment categories
    """
    supabase = get_supabase_client()
    if not supabase:
        logger.warning("Supabase client not available")
        return {
            "positive": 0,
            "neutral": 0,
            "negative": 0,
            "negative_to_positive": 0,
            "neutral_to_positive": 0,
            "neutral_to_negative": 0,
            "positive_to_negative": 0,
        }

    try:
        start_date, end_date = get_period_dates(period, start_date_str, end_date_str)
        config = settings.APP_SETTINGS.supabase

        # Format dates as ISO strings for Supabase (without microseconds)
        query_start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        query_end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(f"Fetching sentiment distribution for period {period}: {query_start_str} to {query_end_str}")

        query = (
            supabase.table(config.sessions_table)
            .select("call_scorecard")
            .gte("call_start_time", query_start_str)
            .lte("call_start_time", query_end_str)
            .eq("IS_FALSE", False)  # Only include valid calls (IS_FALSE=FALSE)
            .not_.is_("call_scorecard", "null")
        )

        response = query.execute()
        logger.info(f"Found {len(response.data)} sessions with scorecard data for sentiment")

        # Initialize counters for all 7 categories
        sentiment_counts = {
            "positive": 0,
            "neutral": 0,
            "negative": 0,
            "negative_to_positive": 0,
            "neutral_to_positive": 0,
            "neutral_to_negative": 0,
            "positive_to_negative": 0,
        }

        for session in response.data:
            scorecard_data = session.get("call_scorecard", {})
            if isinstance(scorecard_data, dict):
                # Get the pre-calculated sentiment shift category
                sentiment_category = scorecard_data.get("sentiment_shift_category")

                # If the field exists and is valid, increment the counter
                if sentiment_category and sentiment_category in sentiment_counts:
                    sentiment_counts[sentiment_category] += 1
                # Handle legacy data without sentiment_shift_category
                # (fallback to old logic for backward compatibility)
                elif not sentiment_category:
                    logger.debug(f"Session missing sentiment_shift_category, using legacy calculation")
                    # This is legacy data - optionally you could recalculate here
                    # For now, we'll just skip it or count as neutral
                    sentiment_counts["neutral"] += 1

        logger.info(f"Sentiment distribution: {sentiment_counts}")
        return sentiment_counts
    except Exception as e:
        logger.error(f"Error fetching sentiment distribution: {e}", exc_info=True)
        return {
            "positive": 0,
            "neutral": 0,
            "negative": 0,
            "negative_to_positive": 0,
            "neutral_to_positive": 0,
            "neutral_to_negative": 0,
            "positive_to_negative": 0,
        }


def get_compliance_scorecard_summary(user_id: Optional[str], period: str, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> Dict[str, int]:
    """
    Get compliance scorecard pass/fail summary.

    Works for both:
    - New calls: Uses stored 'pass' field in categories.compliance
    - Existing calls: Calculates pass/fail from score using threshold (>= 80)

    Args:
        user_id: User ID for tenant filtering (optional)
        period: Time period string

    Returns:
        dict: {"pass_count": int, "fail_count": int, "total_count": int}
    """
    supabase = get_supabase_client()
    if not supabase:
        logger.warning("Supabase client not available")
        return {"pass_count": 0, "fail_count": 0, "total_count": 0}

    try:
        start_date, end_date = get_period_dates(period, start_date_str, end_date_str)
        config = settings.APP_SETTINGS.supabase

        query_start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        query_end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(f"Fetching compliance scorecard summary for period {period}")

        query = (
            supabase.table(config.sessions_table)
            .select("call_scorecard")
            .gte("call_start_time", query_start_str)
            .lte("call_start_time", query_end_str)
            .eq("IS_FALSE", False)  # Only include valid calls (IS_FALSE=FALSE)
            .not_.is_("call_scorecard", "null")
        )

        response = query.execute()
        logger.info(f"Found {len(response.data)} sessions with scorecard data for compliance summary")

        pass_count = 0
        fail_count = 0
        threshold = SCORECARD_THRESHOLDS['compliance']

        for session in response.data:
            scorecard_data = session.get("call_scorecard", {})
            if isinstance(scorecard_data, dict):
                categories = scorecard_data.get("categories", {})
                compliance = categories.get("compliance", {})

                if compliance:
                    # Check if 'pass' field exists (new calls)
                    if "pass" in compliance:
                        if compliance["pass"]:
                            pass_count += 1
                        else:
                            fail_count += 1
                    # Fallback: calculate from score (existing calls)
                    elif "score" in compliance:
                        score = compliance["score"]
                        if score >= threshold:
                            pass_count += 1
                        else:
                            fail_count += 1

        total_count = pass_count + fail_count
        logger.info(f"Compliance summary: {pass_count} passes, {fail_count} fails out of {total_count} total")

        return {
            "pass_count": pass_count,
            "fail_count": fail_count,
            "total_count": total_count,
        }
    except Exception as e:
        logger.error(f"Error fetching compliance scorecard summary: {e}", exc_info=True)
        return {"pass_count": 0, "fail_count": 0, "total_count": 0}


def get_servicing_scorecard_summary(user_id: Optional[str], period: str, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> Dict[str, int]:
    """
    Get servicing scorecard pass/fail summary.

    Works for both:
    - New calls: Uses stored 'pass' field in categories.servicing
    - Existing calls: Calculates pass/fail from score using threshold (>= 70)

    Args:
        user_id: User ID for tenant filtering (optional)
        period: Time period string

    Returns:
        dict: {"pass_count": int, "fail_count": int, "total_count": int}
    """
    supabase = get_supabase_client()
    if not supabase:
        logger.warning("Supabase client not available")
        return {"pass_count": 0, "fail_count": 0, "total_count": 0}

    try:
        start_date, end_date = get_period_dates(period, start_date_str, end_date_str)
        config = settings.APP_SETTINGS.supabase

        query_start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        query_end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(f"Fetching servicing scorecard summary for period {period}")

        query = (
            supabase.table(config.sessions_table)
            .select("call_scorecard")
            .gte("call_start_time", query_start_str)
            .lte("call_start_time", query_end_str)
            .eq("IS_FALSE", False)  # Only include valid calls (IS_FALSE=FALSE)
            .not_.is_("call_scorecard", "null")
        )

        response = query.execute()
        logger.info(f"Found {len(response.data)} sessions with scorecard data for servicing summary")

        pass_count = 0
        fail_count = 0
        threshold = SCORECARD_THRESHOLDS['servicing']

        for session in response.data:
            scorecard_data = session.get("call_scorecard", {})
            if isinstance(scorecard_data, dict):
                categories = scorecard_data.get("categories", {})
                servicing = categories.get("servicing", {})

                if servicing:
                    # Check if 'pass' field exists (new calls)
                    if "pass" in servicing:
                        if servicing["pass"]:
                            pass_count += 1
                        else:
                            fail_count += 1
                    # Fallback: calculate from score (existing calls)
                    elif "score" in servicing:
                        score = servicing["score"]
                        if score >= threshold:
                            pass_count += 1
                        else:
                            fail_count += 1

        total_count = pass_count + fail_count
        logger.info(f"Servicing summary: {pass_count} passes, {fail_count} fails out of {total_count} total")

        return {
            "pass_count": pass_count,
            "fail_count": fail_count,
            "total_count": total_count,
        }
    except Exception as e:
        logger.error(f"Error fetching servicing scorecard summary: {e}", exc_info=True)
        return {"pass_count": 0, "fail_count": 0, "total_count": 0}


def get_collections_scorecard_summary(user_id: Optional[str], period: str, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> Dict[str, int]:
    """
    Get collections scorecard pass/fail summary.

    Works for both:
    - New calls: Uses stored 'pass' field in categories.collections
    - Existing calls: Calculates pass/fail from score using threshold (>= 75)

    Args:
        user_id: User ID for tenant filtering (optional)
        period: Time period string

    Returns:
        dict: {"pass_count": int, "fail_count": int, "total_count": int}
    """
    supabase = get_supabase_client()
    if not supabase:
        logger.warning("Supabase client not available")
        return {"pass_count": 0, "fail_count": 0, "total_count": 0}

    try:
        start_date, end_date = get_period_dates(period, start_date_str, end_date_str)
        config = settings.APP_SETTINGS.supabase

        query_start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        query_end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(f"Fetching collections scorecard summary for period {period}")

        query = (
            supabase.table(config.sessions_table)
            .select("call_scorecard")
            .gte("call_start_time", query_start_str)
            .lte("call_start_time", query_end_str)
            .eq("IS_FALSE", False)  # Only include valid calls (IS_FALSE=FALSE)
            .not_.is_("call_scorecard", "null")
        )

        response = query.execute()
        logger.info(f"Found {len(response.data)} sessions with scorecard data for collections summary")

        pass_count = 0
        fail_count = 0
        threshold = SCORECARD_THRESHOLDS['collections']

        for session in response.data:
            scorecard_data = session.get("call_scorecard", {})
            if isinstance(scorecard_data, dict):
                categories = scorecard_data.get("categories", {})
                collections = categories.get("collections", {})

                if collections:
                    # Check if 'pass' field exists (new calls)
                    if "pass" in collections:
                        if collections["pass"]:
                            pass_count += 1
                        else:
                            fail_count += 1
                    # Fallback: calculate from score (existing calls)
                    elif "score" in collections:
                        score = collections["score"]
                        if score >= threshold:
                            pass_count += 1
                        else:
                            fail_count += 1

        total_count = pass_count + fail_count
        logger.info(f"Collections summary: {pass_count} passes, {fail_count} fails out of {total_count} total")

        return {
            "pass_count": pass_count,
            "fail_count": fail_count,
            "total_count": total_count,
        }
    except Exception as e:
        logger.error(f"Error fetching collections scorecard summary: {e}", exc_info=True)
        return {"pass_count": 0, "fail_count": 0, "total_count": 0}


def _calculate_scorecard_delta(current_summary: Dict[str, int], period: str, scorecard_type: str, user_id: Optional[str], start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> float:
    """
    Calculate period-over-period delta for scorecard pass counts.

    Args:
        current_summary: Current period summary with pass_count, fail_count
        period: Time period string (used to calculate previous period)
        scorecard_type: Type of scorecard ('compliance', 'servicing', 'collections')
        user_id: User ID for tenant filtering
        start_date_str: Optional start date for custom periods
        end_date_str: Optional end date for custom periods

    Returns:
        float: Delta percentage (negative = decline, positive = improvement)
    """
    if current_summary["total_count"] == 0:
        return 0.0

    try:
        # Calculate previous period dates
        current_start, current_end = get_period_dates(period, start_date_str, end_date_str)
        period_length = (current_end - current_start).days

        # Previous period is same length, ending where current starts
        prev_end = current_start - timedelta(seconds=1)
        prev_start = prev_end - timedelta(days=period_length)

        # Format dates for previous period query
        prev_start_str = prev_start.strftime("%Y-%m-%d")
        prev_end_str = prev_end.strftime("%Y-%m-%d")

        logger.info(f"Calculating delta: current period {current_start.date()} to {current_end.date()}, previous period {prev_start.date()} to {prev_end.date()}")

        # Get previous period summary
        if scorecard_type == 'compliance':
            prev_summary = get_compliance_scorecard_summary(user_id, "custom", prev_start_str, prev_end_str)
        elif scorecard_type == 'servicing':
            prev_summary = get_servicing_scorecard_summary(user_id, "custom", prev_start_str, prev_end_str)
        elif scorecard_type == 'collections':
            prev_summary = get_collections_scorecard_summary(user_id, "custom", prev_start_str, prev_end_str)
        else:
            return 0.0

        current_pass = current_summary["pass_count"]
        prev_pass = prev_summary["pass_count"]

        if prev_pass == 0:
            # If no previous data, return 0 (no meaningful comparison)
            return 0.0

        # Calculate percentage change
        delta = ((current_pass - prev_pass) / prev_pass) * 100

        logger.info(f"{scorecard_type} delta: current {current_pass} vs previous {prev_pass} = {delta:.2f}%")

        return round(delta, 2)
    except Exception as e:
        logger.error(f"Error calculating scorecard delta: {e}", exc_info=True)
        return 0.0

