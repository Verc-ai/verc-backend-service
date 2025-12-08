"""
WSGI config for Verc Backend Service.
"""
import os

# Unset proxy environment variables BEFORE any imports
# Cloud Run sets these, causing supabase-py Client.__init__() to receive unexpected 'proxy' argument
# httpx reads these at import time, so we must unset them before httpx is imported
proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'NO_PROXY', 'no_proxy']
for var in proxy_vars:
    if var in os.environ:
        del os.environ[var]

from django.core.wsgi import get_wsgi_application

# Set default settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()

