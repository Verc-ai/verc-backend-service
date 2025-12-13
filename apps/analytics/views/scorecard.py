"""
Scorecard view for business KPIs.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from apps.analytics.services.aggregations import get_scorecard_metrics
from apps.analytics.services.cache import get_cached_scorecard, cache_scorecard
import logging

logger = logging.getLogger(__name__)


class ScorecardView(APIView):
    """
    GET /api/analytics/scorecard/
    
    Returns pre-aggregated KPIs for the dashboard.
    Response format:
    {
        "period": "last_30_days",
        "metrics": {
            "total_calls": 1823,
            "acceptance_rate": 0.42,
            "avg_handle_time_sec": 214,
            "conversion_delta": 0.07
        },
        "trends": {
            "acceptance_rate": {
                "x": ["2025-09-01", "2025-09-02"],
                "y": [0.38, 0.41]
            }
        }
    }
    """
    # TODO: Change back to [IsAuthenticated] before production
    permission_classes = [AllowAny]  # Temporarily allow unauthenticated access for testing
    
    def get(self, request):
        """
        Get scorecard metrics for the current user's tenant.
        
        Query parameters:
        - period: Time period (default: "last_30_days")
            Options: "last_7_days", "last_30_days", "last_90_days", "last_year", "custom"
        - start_date: ISO date string for custom range (required if period="custom")
        - end_date: ISO date string for custom range (required if period="custom")
        """
        period = request.query_params.get('period', 'last_30_days')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        logger.info(f'ScorecardView received: period={period}, start_date={start_date}, end_date={end_date}')
        
        # Handle unauthenticated requests (for testing)
        user = getattr(request, 'user', None)
        user_id = user.id if user and hasattr(user, 'id') else 'anonymous'
        
        # FIX 6: Re-enable caching with proper TTL
        cache_key = f"scorecard:{user_id}:{period}"
        if period == 'custom' and start_date and end_date:
            cache_key = f"scorecard:{user_id}:custom:{start_date}:{end_date}"
        
        # Temporarily disable cache for custom ranges to debug
        cached_data = None
        if period != 'custom':
            cached_data = get_cached_scorecard(cache_key)
            if cached_data:
                logger.info(f'Returning cached scorecard for period: {period}')
                return Response(cached_data, status=status.HTTP_200_OK)
        
        logger.info(f'Fetching fresh scorecard data for period: {period}, user: {user_id}, dates: {start_date} to {end_date}')
        
        try:
            # Get metrics from aggregation service
            metrics_data = get_scorecard_metrics(user, period, start_date, end_date)
            
            logger.info(f'Scorecard data retrieved: period={metrics_data.get("period")}, total_calls={metrics_data.get("metrics", {}).get("total_calls")}')
            
            # Cache the result - 60 seconds TTL for good balance
            cache_scorecard(cache_key, metrics_data, ttl=60)
            
            return Response(metrics_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error fetching scorecard metrics: {e}', exc_info=True)
            return Response(
                {
                    'error': 'Failed to fetch scorecard metrics',
                    'message': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

