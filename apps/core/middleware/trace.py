"""
Trace middleware for distributed tracing support.

Attaches a unique trace ID to every request for tracking requests across
services and components in distributed systems.
"""
import uuid
import logging

logger = logging.getLogger(__name__)


class TraceMiddleware:
    """
    Attach a unique trace ID to every request for distributed tracing.
    
    Extracts trace ID from X-Trace-Id header if present (for distributed
    tracing across services), or generates a new UUID. Adds trace ID to
    both request object and response headers.
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
        Process request and attach trace ID.
        
        Args:
            request: Django HTTP request object
            
        Returns:
            HttpResponse: Response with X-Trace-Id header added
        """
        # Generate or extract trace ID from request header
        trace_id = request.headers.get('X-Trace-Id') or str(uuid.uuid4())
        request.trace_id = trace_id
        
        # Add trace ID to response headers for distributed tracing
        response = self.get_response(request)
        response['X-Trace-Id'] = trace_id
        
        return response

