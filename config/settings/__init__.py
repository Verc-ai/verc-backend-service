"""
Django settings module.
Loads environment-specific settings based on DJANGO_ENV.
"""
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Determine environment
ENV = os.getenv('DJANGO_ENV', 'development')

# Load environment-specific settings
if ENV == 'production':
    from .production import *
elif ENV == 'staging':
    from .staging import *
elif ENV == 'test':
    from .test import *
else:
    from .development import *

