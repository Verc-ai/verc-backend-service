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


def fetch_all_records(query, page_size: int = 1000) -> List[Dict[str, Any]]:
    """
    Fetch all records from a Supabase query using pagination.

    Supabase has a default limit of 1000 records per query. This helper
    fetches data in chunks until all records are retrieved.

    Args:
        query: Supabase query object (already built with filters)
        page_size: Number of records to fetch per page (default: 1000)

    Returns:
        list: All records combined from all pages
    """
    all_data = []
    offset = 0

    while True:
        # Calculate range for this page (inclusive on both ends)
        start = offset
        end = offset + page_size - 1

        try:
            # Clone the query and add range for this page
            # Note: We need to reconstruct the query with range
            # Since Supabase query objects aren't easily cloneable,
            # we'll fetch and check if we got less than page_size
            paginated_query = query.range(start, end)
            response = paginated_query.execute()

            page_data = response.data
            all_data.extend(page_data)

            logger.debug(f"Fetched {len(page_data)} records (offset {offset})")

            # If we got fewer records than page_size, we've reached the end
            if len(page_data) < page_size:
                break

            offset += page_size

        except Exception as e:
            logger.error(f"Error fetching page at offset {offset}: {e}")
            # Return what we have so far rather than failing completely
            break

    logger.info(f"Fetched total of {len(all_data)} records using pagination")
    return all_data


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

        # Use count="exact" with head=True to get count without fetching data
        # This avoids the 1000 record limit since we're only getting the count
        query = (
            supabase.table(config.sessions_table)
            .select("id", count="exact")
            .gte("call_start_time", query_start_str)
            .lte("call_start_time", query_end_str)
            .eq("IS_FALSE", False)  # Only include valid calls (is_false=FALSE)
        )

        # TODO: Add tenant filtering when user_id is provided
        # This requires understanding the tenant/user relationship in your schema

        response = query.execute()
        # Use count attribute directly - it should be accurate with count="exact"
        count = response.count if hasattr(response, 'count') and response.count is not None else 0
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
            .eq("IS_FALSE", False)  # Only include valid calls (is_false=FALSE)
        )

        # Use pagination to fetch all records
        all_sessions = fetch_all_records(query)
        logger.info(f"Found {len(all_sessions)} sessions for acceptance rate calculation")

        if not all_sessions:
            return 0.0

        total = len(all_sessions)
        accepted = 0

        # Check metadata for acceptance status
        # Adjust this logic based on your actual data structure
        for session in all_sessions:
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
    Calculate average handle time in seconds using database aggregation (RPC).

    Args:
        user_id: User ID for tenant filtering (optional)
        period: Time period string
        start_date_str: Optional ISO date string for custom range
        end_date_str: Optional ISO date string for custom range

    Returns:
        float: Average handle time in seconds
    """
    supabase = get_supabase_client()
    if not supabase:
        logger.warning("Supabase client not available")
        return 0.0

    try:
        start_date, end_date = get_period_dates(period, start_date_str, end_date_str)

        # Format dates as ISO strings for Supabase (without microseconds)
        query_start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        query_end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(f"Fetching avg handle time for period {period}: {query_start_str} to {query_end_str}")

        # Use database-level aggregation via RPC for better performance
        response = supabase.rpc(
            'get_avg_call_duration',
            {
                'start_date_param': query_start_str,
                'end_date_param': query_end_str
            }
        ).execute()

        avg_duration = float(response.data) if response.data else 0.0
        logger.info(f"Average handle time: {avg_duration:.2f} seconds (via RPC)")

        return avg_duration
    except Exception as e:
        logger.error(f"Error calculating avg handle time: {e}", exc_info=True)
        return 0.0


def get_total_call_time(user_id: Optional[str], period: str, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> int:
    """
    Calculate total call time (sum of all call durations) in seconds using database aggregation (RPC).

    Args:
        user_id: User ID for tenant filtering (optional)
        period: Time period string
        start_date_str: Optional ISO date string for custom range
        end_date_str: Optional ISO date string for custom range

    Returns:
        int: Total call time in seconds
    """
    supabase = get_supabase_client()
    if not supabase:
        logger.warning("Supabase client not available")
        return 0

    try:
        start_date, end_date = get_period_dates(period, start_date_str, end_date_str)

        # Format dates as ISO strings for Supabase (without microseconds)
        query_start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        query_end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(f"Fetching total call time for period {period}: {query_start_str} to {query_end_str}")

        # Use database-level aggregation via RPC for better performance
        response = supabase.rpc(
            'get_total_call_duration',
            {
                'start_date_param': query_start_str,
                'end_date_param': query_end_str
            }
        ).execute()

        total_seconds = int(response.data) if response.data else 0
        logger.info(f"Total call time: {total_seconds} seconds ({total_seconds / 3600:.2f} hours) (via RPC)")

        return total_seconds
    except Exception as e:
        logger.error(f"Error calculating total call time: {e}", exc_info=True)
        return 0


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

        # Use database-level aggregation for total_calls (much faster)
        if metric == "total_calls":
            try:
                # Use RPC for efficient daily call counts
                response = supabase.rpc(
                    'get_daily_call_counts',
                    {
                        'start_date_param': query_start_str,
                        'end_date_param': query_end_str
                    }
                ).execute()

                # Convert RPC response to the expected format
                date_groups = {}
                for row in (response.data or []):
                    date_str = row['call_date']
                    date_groups[date_str] = [None] * row['call_count']  # Dummy list for count

                logger.info(f"Fetched {len(date_groups)} days of data via RPC for {metric}")

                # Process the date_groups as before (below)
                all_sessions = []  # Not needed for RPC path
            except Exception as rpc_error:
                logger.warning(f"RPC failed, falling back to pagination: {rpc_error}")
                # Fallback to pagination if RPC fails
                query = (
                    supabase.table(config.sessions_table)
                    .select("call_start_time, metadata")
                    .gte("call_start_time", query_start_str)
                    .lte("call_start_time", query_end_str)
                    .eq("IS_FALSE", False)
                )
                all_sessions = fetch_all_records(query)
                logger.info(f"Fetched {len(all_sessions)} sessions with pagination for {metric}")
                date_groups = None  # Will be built below
        else:
            # For acceptance_rate and other metrics, use pagination
            # Fetch all data in the date range in a single query with pagination
            # Use call_start_time for accurate date aggregation (not created_at which is ingestion time)
            query = (
                supabase.table(config.sessions_table)
                .select("call_start_time, metadata")
                .gte("call_start_time", query_start_str)
                .lte("call_start_time", query_end_str)
                .eq("IS_FALSE", False)  # Only include valid calls (IS_FALSE=FALSE)
            )

            # Use pagination to fetch all records (fixes 1000 record cap)
            all_sessions = fetch_all_records(query)
            logger.info(f"Fetched {len(all_sessions)} sessions with pagination for {metric}")
            date_groups = None  # Will be built below
        
        # FIX 7: Downsample for long periods to reduce payload size
        # For periods > 30 days, use weekly aggregation instead of daily
        days_in_period = (end_date - start_date).days
        aggregation_interval = 7 if days_in_period > 30 else 1  # Weekly if > 30 days, daily otherwise

        # Build date_groups if not already built (from RPC)
        if date_groups is None:
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
                # For weekly aggregation, sum up all sessions from the entire week
                if aggregation_interval == 7:
                    # Get sessions for the entire week (7 days starting from current date)
                    week_sessions = []
                    for day_offset in range(7):
                        week_date = current + timedelta(days=day_offset)
                        if week_date > end_date_only:
                            break
                        week_date_str = week_date.strftime("%Y-%m-%d")
                        week_sessions.extend(date_groups.get(week_date_str, []))
                    sessions_for_date = week_sessions
                else:
                    # For daily aggregation, just get sessions for this specific date
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

        # Use pagination to fetch all records
        all_sessions = fetch_all_records(query)
        logger.info(f"Found {len(all_sessions)} sessions with scorecard data for intents")

        intent_counts = {}

        for session in all_sessions:
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


def get_action_codes(user_id: Optional[str], period: str, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> Dict[str, int]:
    """
    Get aggregated action codes count from call summaries.

    Action codes represent the actions taken during calls (e.g., DT=Disaster Team, TC=Third Call, CO=Collections Outbound).

    Args:
        user_id: User ID for tenant filtering (optional)
        period: Time period string
        start_date_str: Optional start date override
        end_date_str: Optional end date override

    Returns:
        dict: {action_code: count} (e.g., {"DT": 15, "TC": 23, "CO": 8})
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            logger.error("Supabase client not available")
            return {}

        start_date, end_date = get_period_dates(period, start_date_str, end_date_str)
        query_start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        query_end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(f"Fetching action codes for period {period}")

        # Query sessions with call_summary data
        config = settings.APP_SETTINGS.supabase
        query = (
            supabase.table(config.sessions_table)
            .select("call_summary")
            .gte("call_start_time", query_start_str)
            .lte("call_start_time", query_end_str)
            .eq("IS_FALSE", False)  # Only include valid calls (IS_FALSE=FALSE)
            .not_.is_("call_summary", "null")
        )

        # Add user filtering if provided
        if user_id:
            query = query.eq("user_id", user_id)

        # Use pagination to fetch all records
        all_sessions = fetch_all_records(query)
        logger.info(f"Found {len(all_sessions)} sessions with call_summary data for action codes")

        action_counts = {}

        for session in all_sessions:
            summary_data = session.get("call_summary", {})
            if isinstance(summary_data, dict):
                action_codes = summary_data.get("action_codes", [])
                if isinstance(action_codes, list):
                    for code in action_codes:
                        if isinstance(code, str):
                            action_counts[code] = action_counts.get(code, 0) + 1

        logger.info(f"Found {len(action_counts)} unique action codes")
        return action_counts
    except Exception as e:
        logger.error(f"Error fetching action codes: {e}", exc_info=True)
        return {}


def get_result_codes(user_id: Optional[str], period: str, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> Dict[str, int]:
    """
    Get aggregated result/outcome codes count from call summaries.

    Result codes represent the outcome of calls (e.g., MP=Made Payment, TT=Transferred to Team, FU=Follow Up Needed).

    Args:
        user_id: User ID for tenant filtering (optional)
        period: Time period string
        start_date_str: Optional start date override
        end_date_str: Optional end date override

    Returns:
        dict: {result_code: count} (e.g., {"MP": 10, "TT": 8, "FU": 12})
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            logger.error("Supabase client not available")
            return {}

        start_date, end_date = get_period_dates(period, start_date_str, end_date_str)
        query_start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        query_end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(f"Fetching result codes for period {period}")

        # Query sessions with call_summary data
        config = settings.APP_SETTINGS.supabase
        query = (
            supabase.table(config.sessions_table)
            .select("call_summary")
            .gte("call_start_time", query_start_str)
            .lte("call_start_time", query_end_str)
            .eq("IS_FALSE", False)  # Only include valid calls (IS_FALSE=FALSE)
            .not_.is_("call_summary", "null")
        )

        # Add user filtering if provided
        if user_id:
            query = query.eq("user_id", user_id)

        # Use pagination to fetch all records
        all_sessions = fetch_all_records(query)
        logger.info(f"Found {len(all_sessions)} sessions with call_summary data for result codes")

        result_counts = {}

        for session in all_sessions:
            summary_data = session.get("call_summary", {})
            if isinstance(summary_data, dict):
                result_codes = summary_data.get("result_codes", [])
                if isinstance(result_codes, list):
                    for code in result_codes:
                        if isinstance(code, str):
                            result_counts[code] = result_counts.get(code, 0) + 1

        logger.info(f"Found {len(result_counts)} unique result codes")
        return result_counts
    except Exception as e:
        logger.error(f"Error fetching result codes: {e}", exc_info=True)
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

        # Use pagination to fetch all records
        all_sessions = fetch_all_records(query)
        logger.info(f"Found {len(all_sessions)} sessions with scorecard data for sentiment")

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

        for session in all_sessions:
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
    Get compliance scorecard pass/fail summary using database aggregation (RPC).

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

        query_start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        query_end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(f"Fetching compliance scorecard summary for period {period}")

        # Use database-level aggregation via RPC for better performance
        threshold = SCORECARD_THRESHOLDS['compliance']
        logger.info(f"DEBUG: Using compliance threshold = {threshold}")
        response = supabase.rpc(
            'get_compliance_summary',
            {
                'start_date_param': query_start_str,
                'end_date_param': query_end_str,
                'threshold_param': threshold
            }
        ).execute()

        # RPC returns a single row with pass_count, fail_count, total_count
        if response.data and len(response.data) > 0:
            result = response.data[0]
            pass_count = int(result['pass_count'])
            fail_count = int(result['fail_count'])
            total_count = int(result['total_count'])
        else:
            pass_count = 0
            fail_count = 0
            total_count = 0

        logger.info(f"Compliance summary: {pass_count} passes, {fail_count} fails out of {total_count} total (via RPC)")

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
    Get servicing scorecard pass/fail summary using database aggregation (RPC).

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

        query_start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        query_end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(f"Fetching servicing scorecard summary for period {period}")

        # Use database-level aggregation via RPC for better performance
        threshold = SCORECARD_THRESHOLDS['servicing']
        response = supabase.rpc(
            'get_servicing_summary',
            {
                'start_date_param': query_start_str,
                'end_date_param': query_end_str,
                'threshold_param': threshold
            }
        ).execute()

        # RPC returns a single row with pass_count, fail_count, total_count
        if response.data and len(response.data) > 0:
            result = response.data[0]
            pass_count = int(result['pass_count'])
            fail_count = int(result['fail_count'])
            total_count = int(result['total_count'])
        else:
            pass_count = 0
            fail_count = 0
            total_count = 0

        logger.info(f"Servicing summary: {pass_count} passes, {fail_count} fails out of {total_count} total (via RPC)")

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
    Get collections scorecard pass/fail summary using database aggregation (RPC).

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

        query_start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        query_end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(f"Fetching collections scorecard summary for period {period}")

        # Use database-level aggregation via RPC for better performance
        threshold = SCORECARD_THRESHOLDS['collections']
        response = supabase.rpc(
            'get_collections_summary',
            {
                'start_date_param': query_start_str,
                'end_date_param': query_end_str,
                'threshold_param': threshold
            }
        ).execute()

        # RPC returns a single row with pass_count, fail_count, total_count
        if response.data and len(response.data) > 0:
            result = response.data[0]
            pass_count = int(result['pass_count'])
            fail_count = int(result['fail_count'])
            total_count = int(result['total_count'])
        else:
            pass_count = 0
            fail_count = 0
            total_count = 0

        logger.info(f"Collections summary: {pass_count} passes, {fail_count} fails out of {total_count} total (via RPC)")

        return {
            "pass_count": pass_count,
            "fail_count": fail_count,
            "total_count": total_count,
        }
    except Exception as e:
        logger.error(f"Error fetching collections scorecard summary: {e}", exc_info=True)
        return {"pass_count": 0, "fail_count": 0, "total_count": 0}


def get_legal_scorecard_summary(user_id: Optional[str], period: str, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> Dict[str, int]:
    """
    Get legal scorecard pass/fail summary using database aggregation (RPC).

    Legal scorecard is based on legal_issues_detected boolean field:
    - Pass: legal_issues_detected = false (no legal risk)
    - Fail: legal_issues_detected = true (legal review required)

    Args:
        user_id: User ID for tenant filtering (optional)
        period: Time period string
        start_date_str: Optional ISO date string for custom range
        end_date_str: Optional ISO date string for custom range

    Returns:
        dict: {"pass_count": int, "fail_count": int, "total_count": int}
    """
    supabase = get_supabase_client()
    if not supabase:
        logger.warning("Supabase client not available")
        return {"pass_count": 0, "fail_count": 0, "total_count": 0}

    try:
        start_date, end_date = get_period_dates(period, start_date_str, end_date_str)

        query_start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        query_end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(f"Fetching legal scorecard summary for period {period}")

        # Use database-level aggregation via RPC for better performance
        threshold = SCORECARD_THRESHOLDS['legal']  # 0, not used but included for consistency
        response = supabase.rpc(
            'get_legal_summary',
            {
                'start_date_param': query_start_str,
                'end_date_param': query_end_str,
                'threshold_param': threshold
            }
        ).execute()

        # RPC returns a single row with pass_count, fail_count, total_count
        if response.data and len(response.data) > 0:
            result = response.data[0]
            pass_count = int(result['pass_count'])
            fail_count = int(result['fail_count'])
            total_count = int(result['total_count'])
        else:
            pass_count = 0
            fail_count = 0
            total_count = 0

        logger.info(f"Legal summary: {pass_count} passes (no legal risk), {fail_count} fails (legal risk detected) out of {total_count} total (via RPC)")

        return {
            "pass_count": pass_count,
            "fail_count": fail_count,
            "total_count": total_count,
        }
    except Exception as e:
        logger.error(f"Error fetching legal scorecard summary: {e}", exc_info=True)
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

