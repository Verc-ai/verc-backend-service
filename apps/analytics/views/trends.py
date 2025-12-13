"""
Trends view for time series analytics.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from apps.analytics.services.aggregations import get_trend_metrics
from apps.analytics.services.cache import get_cached_trends, cache_trends
import logging

logger = logging.getLogger(__name__)


class TrendsView(APIView):
    """
    GET /api/analytics/trends/
    
    Returns time series data for trend visualization.
    Response format:
    {
        "period": "last_30_days",
        "metrics": {
            "acceptance_rate": {
                "x": ["2025-09-01", "2025-09-02", ...],
                "y": [0.38, 0.41, ...]
            },
            "total_calls": {
                "x": ["2025-09-01", "2025-09-02", ...],
                "y": [45, 52, ...]
            }
        }
    }
    """
    # TODO: Change back to [IsAuthenticated] before production
    permission_classes = [AllowAny]  # Temporarily allow unauthenticated access for testing
    
    def get(self, request):
        """
        Get trend metrics for the current user's tenant.
        
        Query parameters:
        - period: Time period (default: "last_30_days")
        - metric: Specific metric to fetch (optional, returns all if not specified)
        """
        period = request.query_params.get('period', 'last_30_days')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        metric = request.query_params.get('metric', None)
        
        logger.info(f'TrendsView received: period={period}, start_date={start_date}, end_date={end_date}, metric={metric}')
        
        # Handle unauthenticated requests (for testing)
        user = getattr(request, 'user', None)
        user_id = user.id if user and hasattr(user, 'id') else 'anonymous'
        
        # FIX 6: Re-enable caching with proper TTL
        cache_key = f"trends:{user_id}:{period}:{metric or 'all'}"
        if period == 'custom' and start_date and end_date:
            cache_key = f"trends:{user_id}:custom:{start_date}:{end_date}:{metric or 'all'}"
        
        # Temporarily disable cache for custom ranges to debug
        cached_data = None
        if period != 'custom':
            cached_data = get_cached_trends(cache_key)
            if cached_data:
                logger.info(f'Returning cached trends for period: {period}')
                return Response(cached_data, status=status.HTTP_200_OK)
        
        logger.info(f'Fetching fresh trends data for period: {period}, dates: {start_date} to {end_date}, metric: {metric}, user: {user_id}')
        
        try:
            # Get trends from aggregation service
            trends_data = get_trend_metrics(user, period, metric, start_date, end_date)
            
            logger.info(f'Trends data retrieved: period={trends_data.get("period")}, metrics={list(trends_data.get("metrics", {}).keys())}')
            
            # Cache the result - 60 seconds TTL
            cache_trends(cache_key, trends_data, ttl=60)
            
            return Response(trends_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error fetching trend metrics: {e}', exc_info=True)
            return Response(
                {
                    'error': 'Failed to fetch trend metrics',
                    'message': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

