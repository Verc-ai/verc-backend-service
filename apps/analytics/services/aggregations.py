"""
Business logic for aggregating analytics data.
Combines raw queries into meaningful business metrics.
"""
from typing import Dict, Any, Optional
from apps.analytics.services.queries import (
    get_sessions_count,
    get_acceptance_rate,
    get_avg_handle_time,
    get_daily_metrics,
    get_period_dates,
    get_call_intents,
    get_sentiment_distribution,
    get_compliance_scorecard_summary,
    get_servicing_scorecard_summary,
    get_collections_scorecard_summary,
    _calculate_scorecard_delta,
)
import logging

logger = logging.getLogger(__name__)


def get_scorecard_metrics(user, period: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Get aggregated scorecard metrics for the dashboard.
    
    Args:
        user: Django user object (for tenant filtering)
        period: Time period string
        start_date: Optional ISO date string for custom range
        end_date: Optional ISO date string for custom range
        
    Returns:
        dict: Scorecard data with metrics and trends
    """
    user_id = str(user.id) if user else None
    
    # Get main metrics
    total_calls = get_sessions_count(user_id, period, start_date, end_date)
    acceptance_rate = get_acceptance_rate(user_id, period, start_date, end_date)
    avg_handle_time_sec = get_avg_handle_time(user_id, period, start_date, end_date)
    
    # Calculate conversion delta (placeholder - adjust based on your business logic)
    # This compares current period to previous period
    conversion_delta = 0.07  # Placeholder - implement actual comparison
    
    # Get trend data for acceptance rate
    acceptance_trend = get_daily_metrics(user_id, period, "acceptance_rate", start_date, end_date)
    
    # Get call intents and sentiment distribution
    call_intents = get_call_intents(user_id, period, start_date, end_date)
    sentiment_dist = get_sentiment_distribution(user_id, period, start_date, end_date)
    
    return {
        "period": period,
        "metrics": {
            "total_calls": total_calls,
            "acceptance_rate": round(acceptance_rate, 2),
            "avg_handle_time_sec": round(avg_handle_time_sec, 0),
            "conversion_delta": conversion_delta,
        },
        "trends": {
            "acceptance_rate": acceptance_trend,
        },
        "call_intents": call_intents,
        "sentiment_distribution": sentiment_dist,
    }


def get_trend_metrics(user, period: str, metric: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Get trend metrics for time series visualization.
    
    Args:
        user: Django user object (for tenant filtering)
        period: Time period string
        metric: Specific metric to fetch (optional)
        start_date: Optional ISO date string for custom range
        end_date: Optional ISO date string for custom range
        
    Returns:
        dict: Trend data with time series for requested metrics
    """
    user_id = str(user.id) if user else None
    
    metrics_to_fetch = [metric] if metric else ["acceptance_rate", "total_calls"]
    
    trends_data = {
        "period": period,
        "metrics": {}
    }
    
    for m in metrics_to_fetch:
        trends_data["metrics"][m] = get_daily_metrics(user_id, period, m, start_date, end_date)
    
    return trends_data


def get_health_metrics(user, period: str) -> Dict[str, Any]:
    """
    Get system and quality health metrics.
    
    Args:
        user: Django user object (for tenant filtering)
        period: Time period string
        
    Returns:
        dict: Health metrics data
    """
    user_id = str(user.id) if user else None
    
    # Placeholder metrics - implement based on your actual system monitoring
    # These would typically come from error logs, response time tracking, etc.
    
    return {
        "period": period,
        "metrics": {
            "avg_response_time_ms": 245,  # Placeholder
            "error_rate": 0.02,  # Placeholder
            "uptime_percentage": 99.8,  # Placeholder
            "total_errors": 12,  # Placeholder
        }
    }


def get_scorecard_summaries(user, period: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Get pass/fail summaries for all scorecard categories with delta calculations.

    Returns counts and percentages for compliance, servicing, and collections scorecards.
    Works for both existing calls (calculated on-the-fly) and new calls (pre-stored pass/fail).

    Args:
        user: Django user object (for tenant filtering)
        period: Time period string
        start_date: Optional ISO date string for custom range
        end_date: Optional ISO date string for custom range

    Returns:
        dict: Scorecard summaries with pass/fail counts, percentages, and deltas
    """
    user_id = str(user.id) if user else None

    # Get summaries for each scorecard type
    compliance_summary = get_compliance_scorecard_summary(user_id, period, start_date, end_date)
    servicing_summary = get_servicing_scorecard_summary(user_id, period, start_date, end_date)
    collections_summary = get_collections_scorecard_summary(user_id, period, start_date, end_date)

    # Calculate deltas
    compliance_delta = _calculate_scorecard_delta(compliance_summary, period, 'compliance', user_id, start_date, end_date)
    servicing_delta = _calculate_scorecard_delta(servicing_summary, period, 'servicing', user_id, start_date, end_date)
    collections_delta = _calculate_scorecard_delta(collections_summary, period, 'collections', user_id, start_date, end_date)

    # Build response with pass percentages
    def build_summary(summary, delta):
        total = summary["total_count"]
        pass_count = summary["pass_count"]
        fail_count = summary["fail_count"]
        pass_percentage = round((pass_count / total * 100), 2) if total > 0 else 0.0

        return {
            "pass_count": pass_count,
            "fail_count": fail_count,
            "total_count": total,
            "pass_percentage": pass_percentage,
            "delta_percentage": delta,
        }

    return {
        "compliance": build_summary(compliance_summary, compliance_delta),
        "servicing": build_summary(servicing_summary, servicing_delta),
        "collections": build_summary(collections_summary, collections_delta),
    }

