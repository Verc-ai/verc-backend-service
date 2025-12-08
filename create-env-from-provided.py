#!/usr/bin/env python3
"""
Create Django .env file from provided environment variables.
"""
from pathlib import Path

DJANGO_ENV_PATH = Path(__file__).parent / '.env'

# Environment variables from your TypeScript .env file
env_content = """# Django Backend Service Environment Variables
# Generated from TypeScript backend configuration

# Django Settings
DJANGO_ENV=development
SECRET_KEY=django-insecure-change-me-in-production-use-strong-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Server
API_PORT=4000
PORT=4000

# Supabase Configuration
SUPABASE_URL=your-supabase-url-here
SUPABASE_ANON_KEY=your-supabase-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key-here

# Supabase Table Names
SUPABASE_TRANSCRIPTIONS_TABLE=transcription_events
SUPABASE_SESSIONS_TABLE=transcription_sessions
SUPABASE_PROFILES_TABLE=profiles
SUPABASE_SOPS_TABLE=sops
SUPABASE_SOP_RULES_TABLE=sop_rules
SUPABASE_SOP_LOGS_TABLE=sop_processing_logs
SUPABASE_FEATURE_FLAGS_TABLE=feature_flags

# Supabase Storage Buckets
SUPABASE_SOPS_BUCKET=sops
SUPABASE_AUDIO_BUCKET=audio-files

# AI Provider API Keys
# OpenAI (required for GPT-5 models)
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_ORGANIZATION=
OPENAI_MAX_RETRIES=3
OPENAI_TIMEOUT=600000
OPENAI_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
OPENAI_TRANSCRIPTION_LANGUAGE=

# Anthropic (optional, used as fallback)
ANTHROPIC_API_KEY=your-anthropic-api-key-here
ANTHROPIC_MAX_RETRIES=3
ANTHROPIC_TIMEOUT=600000

# AssemblyAI (required for conversation/audio features)
ASSEMBLYAI_API_KEY=your-assemblyai-api-key-here
ASSEMBLYAI_PII_REDACTION_ENABLED=true
ASSEMBLYAI_PII_SUBSTITUTION=entity_name
ASSEMBLYAI_GENERATE_REDACTED_AUDIO=true

# LandingAI (required for PDF/document OCR extraction)
LANDINGAI_API_KEY=your-landingai-api-key-here

# AI Provider Configuration
AI_PRIMARY_PROVIDER=openai
AI_FALLBACK_PROVIDER=anthropic
AI_ENABLE_FALLBACK=true

# Model Configuration (GPT-5 Optimized for Cost/Performance)
SOP_STAGE_DISCOVERY_MODEL=gpt-5-mini
SOP_RULE_EXTRACTION_MODEL=gpt-5-nano
SOP_EXAMPLE_EXTRACTION_MODEL=gpt-5-nano
SOP_FLOW_EXTRACTION_MODEL=gpt-5-mini
SOP_VALIDATION_MODEL=gpt-5-mini
SOP_FORMATTING_MODEL=gpt-5-nano
SOP_REVIEW_MODEL=claude-sonnet-4-20250514
SOP_VISION_MODEL=gpt-5

# Twilio Configuration
TWILIO_ACCOUNT_SID=your-twilio-account-sid-here
TWILIO_AUTH_TOKEN=your-twilio-auth-token-here
TWILIO_PHONE_NUMBER=+18555570804
TWILIO_WEBHOOK_BASE_URL=https://verc-backend.ngrok.app
TWILIO_AGENT_NUMBER=+19382041709
TWILIO_TRANSCRIPTION_PROVIDER=google
TWILIO_INTELLIGENCE_SERVICE_SID=GA91eaac2537cf7e9c60060e50f050647e

# Google Cloud Tasks (if using)
CLOUD_TASKS_ENABLED=false
GCP_PROJECT_ID=
GCP_REGION=
GCP_TASK_QUEUE_NAME=transcription-queue
CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL=

# Redis (for Channels/WebSocket support)
REDIS_URL=redis://localhost:6379/0

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Logging
LOG_LEVEL=DEBUG

# Asterisk ARI (Real-time Audio) - for future use
ARI_URL=your-ari-url-here
ARI_USER=your-ari-user-here
ARI_PASSWORD=your-ari-password-here
ARI_STASIS_APP=verc-realtime-audio
"""

def main():
    if DJANGO_ENV_PATH.exists():
        backup_path = DJANGO_ENV_PATH.with_suffix('.env.backup')
        print(f"⚠️  .env file already exists. Backing up to {backup_path}")
        DJANGO_ENV_PATH.rename(backup_path)
    
    DJANGO_ENV_PATH.write_text(env_content)
    print(f"✅ Created Django .env file at: {DJANGO_ENV_PATH}")
    print("\n📝 Important: Update SECRET_KEY for production use!")
    print("   You can generate a new one with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'")

if __name__ == '__main__':
    main()

