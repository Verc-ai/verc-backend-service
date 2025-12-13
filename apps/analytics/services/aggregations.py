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

