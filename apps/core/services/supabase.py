"""
Supabase client service.

Provides singleton Supabase clients for both service role (admin) operations
and anonymous key (user authentication) operations. Handles proxy environment
variable cleanup required for Cloud Run deployments.
"""
from typing import Optional
from supabase import create_client, Client
from django.conf import settings
import logging
import os

logger = logging.getLogger(__name__)

# Unset proxy environment variables at module load to prevent httpx from passing
# proxy argument to Supabase Client. Cloud Run may set these, causing supabase-py
# Client.__init__() to receive unexpected 'proxy' argument.
_proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'NO_PROXY', 'no_proxy']
_original_proxy_env = {}
for var in _proxy_vars:
    if var in os.environ:
        _original_proxy_env[var] = os.environ[var]
        del os.environ[var]

_supabase_client: Optional[Client] = None
_supabase_auth_client: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    """
    Get or create Supabase client singleton with service role key.
    
    This client has admin privileges and should be used for operations that
    require elevated permissions. Uses singleton pattern to reuse the same
    client instance across the application.
    
    Returns:
        Optional[Client]: Supabase client instance, or None if configuration is missing
        
    Note:
        Returns None if configuration is incomplete, allowing fallback to mock
        authentication in development environments.
    """
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
    
    config = settings.APP_SETTINGS.supabase
    
    if not config.url or not config.service_role_key:
        logger.warning('Supabase configuration incomplete - missing URL or service role key')
        return None
    
    try:
        # Proxy env vars already unset at module load, so create client directly
        # Service role key automatically bypasses RLS in Supabase v1.2.0
        _supabase_client = create_client(
            config.url,
            config.service_role_key
        )
        logger.debug('Supabase client created successfully with service role authorization')
        return _supabase_client
    except Exception as e:
        logger.error(f'Failed to create Supabase client: {e}')
        # Return None to allow fallback to mock authentication
        return None


def get_supabase_auth_client() -> Optional[Client]:
    """
    Get or create Supabase client singleton with anonymous key.
    
    This client is used for user authentication operations and respects
    Row Level Security (RLS) policies. Uses singleton pattern to reuse the
    same client instance across the application.
    
    Returns:
        Optional[Client]: Supabase client instance, or None if configuration is missing
        
    Note:
        Returns None if configuration is incomplete, allowing fallback to mock
        authentication in development environments.
    """
    global _supabase_auth_client
    
    if _supabase_auth_client is not None:
        return _supabase_auth_client
    
    config = settings.APP_SETTINGS.supabase
    
    if not config.url or not config.anon_key:
        return None
    
    try:
        # Proxy env vars already unset at module load, so create client directly
        _supabase_auth_client = create_client(
            config.url,
            config.anon_key
        )
        logger.debug('Supabase auth client created successfully')
        return _supabase_auth_client
    except Exception as e:
        logger.error(f'Failed to create Supabase auth client: {e}')
        # Return None to allow fallback to mock authentication
        return None

