"""
Base Django settings for Verc Backend Service.
Production-ready configuration with async support.
"""
import os
from pathlib import Path
from typing import List

import environ
from pydantic import BaseModel, Field

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, ''),
    ALLOWED_HOSTS=(list, []),
)

# Read .env file if it exists
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))


class DatabaseConfig(BaseModel):
    """Database configuration."""
    url: str = Field(..., description="Database URL")
    engine: str = Field(default="django.db.backends.postgresql")
    name: str = ""
    user: str = ""
    password: str = ""
    host: str = ""
    port: str = "5432"
    conn_max_age: int = Field(default=600, description="Connection pool max age")
    options: dict = Field(default_factory=dict)


class SupabaseConfig(BaseModel):
    """Supabase configuration."""
    url: str = ""
    anon_key: str = ""
    service_role_key: str = ""
    events_table: str = "transcription_events"
    sessions_table: str = "transcription_sessions"
    profiles_table: str = "profiles"
    sops_table: str = "sops"
    sop_rules_table: str = "sop_rules"
    sop_logs_table: str = "sop_processing_logs"
    feature_flags_table: str = "feature_flags"
    sops_bucket: str = "sops"
    audio_bucket: str = "audio-files"


class AIConfig(BaseModel):
    """AI provider configuration."""
    # OpenAI
    openai_api_key: str = ""
    openai_organization: str = ""
    openai_max_retries: int = 3
    openai_timeout: int = 600000
    openai_transcription_model: str = "gpt-4o-mini-transcribe"
    openai_transcription_language: str = ""
    
    # Anthropic
    anthropic_api_key: str = ""
    anthropic_max_retries: int = 3
    anthropic_timeout: int = 600000
    
    # AssemblyAI
    assemblyai_api_key: str = ""
    assemblyai_pii_redaction_enabled: bool = False
    assemblyai_pii_substitution: str = "hash"
    assemblyai_generate_redacted_audio: bool = False
    
    # LandingAI
    landingai_api_key: str = ""
    
    # Provider selection
    primary_provider: str = "openai"
    fallback_provider: str = ""
    enable_fallback: bool = True
    
    # SOP Models
    sop_stage_discovery_model: str = "gpt-5-mini"
    sop_rule_extraction_model: str = "gpt-5-mini"
    sop_example_extraction_model: str = "gpt-5-mini"
    sop_flow_extraction_model: str = "gpt-5-mini"


class TwilioConfig(BaseModel):
    """Twilio configuration."""
    account_sid: str = ""
    auth_token: str = ""
    phone_number: str = ""
    webhook_base_url: str = ""
    agent_number: str = ""
    transcription_provider: str = "deepgram"
    intelligence_service_sid: str = ""


class BuffaloPBXConfig(BaseModel):
    """Buffalo PBX configuration for call monitoring."""

    # WebSocket connection
    wss_url: str = Field(
        default="wss://pbx.hovernetworks.net/spop",
        description="Buffalo PBX WebSocket SPOP URL"
    )
    username: str = Field(default="", description="PBX login username")
    password: str = Field(default="", description="PBX login password")

    # SIP credentials for SPY calls
    sip_host: str = Field(default="142.93.69.92", description="SIP server host")
    sip_port: int = Field(default=5060, description="SIP server port")
    sip_username: str = Field(default="", description="SIP auth username")
    sip_password: str = Field(default="", description="SIP auth password")

    # Monitoring settings
    reconnect_delay: int = Field(default=5, description="Reconnect delay in seconds")
    max_reconnect_delay: int = Field(default=60, description="Max reconnect delay")
    ping_interval: int = Field(default=30, description="WebSocket ping interval")
    ping_timeout: int = Field(default=10, description="WebSocket ping timeout")


class CloudTasksConfig(BaseModel):
    """Google Cloud Tasks configuration."""
    enabled: bool = False
    project_id: str = ""
    region: str = ""
    queue_name: str = "transcription-queue"
    service_account_email: str = ""


class AppSettings:
    """Application settings loaded from environment."""
    def __init__(self):
        # Django core
        self.secret_key = env('SECRET_KEY', default='django-insecure-change-me-in-production')
        self.debug = env.bool('DEBUG', default=False)
        self.allowed_hosts = env.list('ALLOWED_HOSTS', default=[])
        
        # Server
        self.api_port = int(os.getenv('PORT', os.getenv('API_PORT', '8080')))
        
        # Database
        self.database = DatabaseConfig(
            url=env('DATABASE_URL', default=''),
            name=env('DB_NAME', default=''),
            user=env('DB_USER', default=''),
            password=env('DB_PASSWORD', default=''),
            host=env('DB_HOST', default=''),
            port=env('DB_PORT', default='5432'),
        )
        
        # Supabase
        self.supabase = SupabaseConfig(
            url=env('SUPABASE_URL', default=''),
            anon_key=env('SUPABASE_ANON_KEY', default=''),
            service_role_key=env('SUPABASE_SERVICE_ROLE_KEY', default=''),
            events_table=env('SUPABASE_TRANSCRIPTIONS_TABLE', default='transcription_events'),
            sessions_table=env('SUPABASE_SESSIONS_TABLE', default='transcription_sessions'),
            profiles_table=env('SUPABASE_PROFILES_TABLE', default='profiles'),
            sops_table=env('SUPABASE_SOPS_TABLE', default='sops'),
            sop_rules_table=env('SUPABASE_SOP_RULES_TABLE', default='sop_rules'),
            sop_logs_table=env('SUPABASE_SOP_LOGS_TABLE', default='sop_processing_logs'),
            feature_flags_table=env('SUPABASE_FEATURE_FLAGS_TABLE', default='feature_flags'),
            sops_bucket=env('SUPABASE_SOPS_BUCKET', default='sops'),
            audio_bucket=env('SUPABASE_AUDIO_BUCKET', default='audio-files'),
        )
        
        # AI
        self.ai = AIConfig(
            openai_api_key=env('OPENAI_API_KEY', default=''),
            openai_organization=env('OPENAI_ORGANIZATION', default=''),
            openai_max_retries=int(env('OPENAI_MAX_RETRIES', default='3')),
            openai_timeout=int(env('OPENAI_TIMEOUT', default='600000')),
            openai_transcription_model=env('OPENAI_TRANSCRIPTION_MODEL', default='gpt-4o-mini-transcribe'),
            openai_transcription_language=env('OPENAI_TRANSCRIPTION_LANGUAGE', default=''),
            anthropic_api_key=env('ANTHROPIC_API_KEY', default=''),
            anthropic_max_retries=int(env('ANTHROPIC_MAX_RETRIES', default='3')),
            anthropic_timeout=int(env('ANTHROPIC_TIMEOUT', default='600000')),
            assemblyai_api_key=env('ASSEMBLYAI_API_KEY', default=''),
            assemblyai_pii_redaction_enabled=env.bool('ASSEMBLYAI_PII_REDACTION_ENABLED', default=False),
            assemblyai_pii_substitution=env('ASSEMBLYAI_PII_SUBSTITUTION', default='hash'),
            assemblyai_generate_redacted_audio=env.bool('ASSEMBLYAI_GENERATE_REDACTED_AUDIO', default=False),
            landingai_api_key=env('LANDINGAI_API_KEY', default=''),
            primary_provider=env('AI_PRIMARY_PROVIDER', default='openai'),
            fallback_provider=env('AI_FALLBACK_PROVIDER', default=''),
            enable_fallback=env.bool('AI_ENABLE_FALLBACK', default=True),
            sop_stage_discovery_model=env('SOP_STAGE_DISCOVERY_MODEL', default='gpt-5-mini'),
            sop_rule_extraction_model=env('SOP_RULE_EXTRACTION_MODEL', default='gpt-5-mini'),
            sop_example_extraction_model=env('SOP_EXAMPLE_EXTRACTION_MODEL', default='gpt-5-mini'),
            sop_flow_extraction_model=env('SOP_FLOW_EXTRACTION_MODEL', default='gpt-5-mini'),
        )
        
        # Twilio
        self.twilio = TwilioConfig(
            account_sid=env('TWILIO_ACCOUNT_SID', default=''),
            auth_token=env('TWILIO_AUTH_TOKEN', default=''),
            phone_number=env('TWILIO_PHONE_NUMBER', default=''),
            webhook_base_url=env('TWILIO_WEBHOOK_BASE_URL', default=''),
            agent_number=env('TWILIO_AGENT_NUMBER', default=''),
            transcription_provider=env('TWILIO_TRANSCRIPTION_PROVIDER', default='deepgram'),
            intelligence_service_sid=env('TWILIO_INTELLIGENCE_SERVICE_SID', default=''),
        )

        # Buffalo PBX
        self.buffalo_pbx = BuffaloPBXConfig(
            wss_url=env('BUFFALO_PBX_WSS_URL', default='wss://pbx.hovernetworks.net/spop'),
            username=env('BUFFALO_PBX_USERNAME', default=''),
            password=env('BUFFALO_PBX_PASSWORD', default=''),
            sip_host=env('BUFFALO_SIP_HOST', default='142.93.69.92'),
            sip_port=int(env('BUFFALO_SIP_PORT', default='5060')),
            sip_username=env('BUFFALO_SIP_USERNAME', default=''),
            sip_password=env('BUFFALO_SIP_PASSWORD', default=''),
        )

        # Cloud Tasks
        self.cloud_tasks = CloudTasksConfig(
            enabled=env.bool('CLOUD_TASKS_ENABLED', default=False),
            project_id=env('GCP_PROJECT_ID', default=''),
            region=env('GCP_REGION', default=''),
            queue_name=env('GCP_TASK_QUEUE_NAME', default='transcription-queue'),
            service_account_email=env('CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL', default=''),
        )
        
        # Logging
        self.log_level = env('LOG_LEVEL', default='INFO')


# Load settings from environment
_settings = AppSettings()

# Django settings
SECRET_KEY = _settings.secret_key
DEBUG = _settings.debug
ALLOWED_HOSTS = _settings.allowed_hosts or ['*']  # Cloud Run handles this

# Cloud Run proxy configuration
# Cloud Run sits behind Google's load balancer, so we need to trust proxy headers
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # Trust Cloud Run's proxy
USE_X_FORWARDED_HOST = True  # Trust X-Forwarded-Host header from Cloud Run
USE_X_FORWARDED_PORT = True  # Trust X-Forwarded-Port header from Cloud Run

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party
    'rest_framework',
    'corsheaders',
    'channels',
    
    # Local apps
    'apps.core',
    'apps.authentication',
    'apps.twilio',
    'apps.ai',
    'apps.call_sessions',
    'apps.conversations',
    'apps.administration',
    'apps.feature_flags',
    'apps.tasks',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',  # Enabled with SECURE_PROXY_SSL_HEADER for Cloud Run
    # corsheaders MUST be early to handle OPTIONS before URL routing (like Express's cors())
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # CommonMiddleware disabled to prevent trailing slash redirects
    # 'django.middleware.common.CommonMiddleware',  # DISABLED - was causing 301 redirects
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Custom middleware
    'apps.core.middleware.trace.TraceMiddleware',
    'apps.core.middleware.tenant.TenantMiddleware',
]

ROOT_URLCONF = 'config.urls'

# Disable APPEND_SLASH to prevent 301 redirects on API endpoints
APPEND_SLASH = False

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database
if _settings.database.url:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(_settings.database.url, conn_max_age=_settings.database.conn_max_age)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': _settings.database.engine,
            'NAME': _settings.database.name,
            'USER': _settings.database.user,
            'PASSWORD': _settings.database.password,
            'HOST': _settings.database.host,
            'PORT': _settings.database.port,
            'OPTIONS': _settings.database.options,
            'CONN_MAX_AGE': _settings.database.conn_max_age,
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
}

# CORS - Allow frontend to connect
# Configured like Express's cors() middleware - handles OPTIONS automatically
# Allow all origins for now (can be restricted later for security)
# This allows localhost frontend to connect to Cloud Run backend
CORS_ALLOW_ALL_ORIGINS = True  # Allow all origins (localhost frontend to Cloud Run)
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'http://localhost:5173',  # Vite dev server
    'http://localhost:3000',  # Alternative frontend port
    'http://127.0.0.1:5173',
    'http://127.0.0.1:3000',
    'http://localhost:5174',  # Alternative Vite port
])
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
CORS_PREFLIGHT_MAX_AGE = 86400  # 24 hours

# Channels (for async/WebSocket support)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [env('REDIS_URL', default='redis://localhost:6379/0')],
        },
    },
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d',
        },
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json' if not DEBUG else 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': _settings.log_level,
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': _settings.log_level,
            'propagate': False,
        },
    },
}

# Export settings for use in other modules
APP_SETTINGS = _settings

