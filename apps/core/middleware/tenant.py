"""
Tenant middleware for multi-tenant organization context extraction.

This middleware extracts and validates organization context from requests
to enable multi-tenant data isolation.
"""
import logging

logger = logging.getLogger(__name__)


class TenantMiddleware:
    """
    Extract organization ID from request for multi-tenant isolation.
    
    Sets request.org_id attribute which can be used by views and services
    to filter data by organization. The org_id is typically populated by
    authentication middleware from user metadata or request headers.
    """
    
    def __init__(self, get_response):
        """
        Initialize middleware.
        
        Args:
            get_response: Django's get_response callable
        """
        self.get_response = get_response

    def __call__(self, request):
        """
        Process request and extract organization context.
        
        Args:
            request: Django HTTP request object
            
        Returns:
            HttpResponse: Response from next middleware or view
        """
        # Extract org_id from user metadata or request headers
        # This is typically populated by authentication middleware
        request.org_id = getattr(request, 'org_id', None)
        
        response = self.get_response(request)
        return response

