"""
Production settings.
Optimized for Google Cloud Run deployment.
"""
from .base import *
import os

DEBUG = False

# Explicitly disable APPEND_SLASH to prevent 301 redirects
APPEND_SLASH = False

# -------------------------
# Security settings
# -------------------------
SECURE_SSL_REDIRECT = False  # Cloud Run handles HTTPS at ingress
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ALLOWED_HOSTS should be set via environment variable in Cloud Run

# -------------------------
# Static files
# -------------------------
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# -------------------------
# Logging (Cloud Logging friendly)
# -------------------------
LOGGING["root"]["level"] = "INFO"
LOGGING["handlers"]["console"]["formatter"] = "json"

# -------------------------
# Caching
# -------------------------
# In-memory cache is fine for Cloud Run (per-instance)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# -------------------------
# GCP-specific
# -------------------------
USE_TZ = True
