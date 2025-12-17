"""
Staging settings.
"""
from .base import *

DEBUG = False

# Explicitly disable APPEND_SLASH to prevent 301 redirects (inherited from base, but ensure it's set)
APPEND_SLASH = False

# Security settings for staging
# SECURE_SSL_REDIRECT is handled by Cloud Run's ingress, so we don't need it
# SECURE_PROXY_SSL_HEADER is set in base.py to trust Cloud Run's proxy
SECURE_SSL_REDIRECT = False  # Cloud Run handles HTTPS at ingress level
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Allowed hosts should be set via environment variable
# ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

# Logging
LOGGING['root']['level'] = 'INFO'

# Cache backend (use in-memory cache to avoid Redis dependency in Cloud Run)
# Feature flags are cached for 60s and rarely change, so per-instance cache is fine
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

