"""
Custom permissions for analytics endpoints.
"""
from rest_framework import permissions


class IsAnalyticsUser(permissions.BasePermission):
    """
    Permission class to check if user has access to analytics.
    
    This can be extended to check for specific roles or feature flags.
    """
    
    def has_permission(self, request, view):
        """
        Check if user has permission to access analytics.
        
        Args:
            request: Django request object
            view: View instance
            
        Returns:
            bool: True if user has permission
        """
        # For now, any authenticated user can access analytics
        # This can be extended to check for specific roles or feature flags
        return request.user and request.user.is_authenticated

