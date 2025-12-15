"""
Production settings.
Optimized for Google Cloud Run deployment.
"""
from .base import *

DEBUG = False

# Explicitly disable APPEND_SLASH to prevent 301 redirects (inherited from base, but ensure it's set)
APPEND_SLASH = False

# Security settings
# SECURE_SSL_REDIRECT is handled by Cloud Run's ingress, so we don't need it
# SECURE_PROXY_SSL_HEADER is set in base.py to trust Cloud Run's proxy
SECURE_SSL_REDIRECT = False  # Cloud Run handles HTTPS at ingress level
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Allowed hosts - Cloud Run handles this, but set explicitly
# ALLOWED_HOSTS should be set via environment variable

# Database connection pooling for production
DATABASES['default']['CONN_MAX_AGE'] = 600

# Static files - served by Cloud Run or CDN
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Logging - structured JSON logs for Cloud Logging
LOGGING['root']['level'] = 'INFO'
LOGGING['handlers']['console']['formatter'] = 'json'

# Performance optimizations
if not DEBUG:
    # Cache backend (use in-memory cache to avoid Redis dependency in Cloud Run)
    # Feature flags are cached for 60s and rarely change, so per-instance cache is fine
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }

# GCP-specific settings
USE_TZ = True

