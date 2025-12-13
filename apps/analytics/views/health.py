"""
Health view for system/quality metrics.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from apps.analytics.services.aggregations import get_health_metrics
from apps.analytics.services.cache import get_cached_health, cache_health
import logging

logger = logging.getLogger(__name__)


class HealthView(APIView):
    """
    GET /api/analytics/health/
    
    Returns system and quality metrics.
    Response format:
    {
        "period": "last_30_days",
        "metrics": {
            "avg_response_time_ms": 245,
            "error_rate": 0.02,
            "uptime_percentage": 99.8,
            "total_errors": 12
        }
    }
    """
    # TODO: Change back to [IsAuthenticated] before production
    permission_classes = [AllowAny]  # Temporarily allow unauthenticated access for testing
    
    def get(self, request):
        """
        Get health metrics for the current user's tenant.
        
        Query parameters:
        - period: Time period (default: "last_30_days")
        """
        period = request.query_params.get('period', 'last_30_days')
        
        # Handle unauthenticated requests (for testing)
        user = getattr(request, 'user', None)
        user_id = user.id if user and hasattr(user, 'id') else 'anonymous'
        
        # Check cache first
        cache_key = f"health:{user_id}:{period}"
        cached_data = get_cached_health(cache_key)
        if cached_data:
            logger.info(f'Returning cached health metrics for period: {period}')
            return Response(cached_data, status=status.HTTP_200_OK)
        
        try:
            # Get health metrics from aggregation service
            health_data = get_health_metrics(user, period)
            
            # Cache the result
            cache_health(cache_key, health_data, ttl=300)  # 5 minutes
            
            return Response(health_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error fetching health metrics: {e}', exc_info=True)
            return Response(
                {
                    'error': 'Failed to fetch health metrics',
                    'message': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

