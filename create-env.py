#!/usr/bin/env python3
"""
Script to create .env file from the TypeScript backend .env file.
This helps migrate environment variables to Django format.
"""
import os
import sys
from pathlib import Path

# Path to the TypeScript backend .env file
TS_ENV_PATH = Path(__file__).parent.parent / '.env'
DJANGO_ENV_PATH = Path(__file__).parent / '.env'

def read_ts_env():
    """
    Read environment variables from TypeScript backend .env file.
    
    Returns:
        dict: Dictionary of environment variable key-value pairs
        
    Raises:
        SystemExit: If the TypeScript .env file is not found
    """
    if not TS_ENV_PATH.exists():
        print(f"Error: TypeScript .env file not found at: {TS_ENV_PATH}")
        print("Please ensure the .env file exists in the parent directory.")
        sys.exit(1)
    
    env_vars = {}
    with open(TS_ENV_PATH, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            # Parse key=value
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars

def create_django_env(ts_vars):
    """
    Create Django .env file configuration from TypeScript environment variables.
    
    Maps TypeScript backend environment variables to Django format and
    provides default values for Django-specific settings.
    
    Args:
        ts_vars: Dictionary of TypeScript environment variables
        
    Returns:
        dict: Dictionary of Django environment variables
    """
    django_vars = {
        # Django-specific
        'DJANGO_ENV': 'development',
        'SECRET_KEY': 'django-insecure-change-me-in-production-use-strong-secret-key',
        'DEBUG': 'True',
        'ALLOWED_HOSTS': 'localhost,127.0.0.1,0.0.0.0',
        
        # Server
        'API_PORT': ts_vars.get('API_PORT', '4000'),
        'PORT': ts_vars.get('API_PORT', '4000'),
        
        # Supabase
        'SUPABASE_URL': ts_vars.get('SUPABASE_URL', ''),
        'SUPABASE_ANON_KEY': ts_vars.get('SUPABASE_ANON_KEY', ''),
        'SUPABASE_SERVICE_ROLE_KEY': ts_vars.get('SUPABASE_SERVICE_ROLE_KEY', ''),
        'SUPABASE_TRANSCRIPTIONS_TABLE': ts_vars.get('SUPABASE_TRANSCRIPTIONS_TABLE', 'transcription_events'),
        'SUPABASE_SESSIONS_TABLE': ts_vars.get('SUPABASE_SESSIONS_TABLE', 'transcription_sessions'),
        'SUPABASE_PROFILES_TABLE': ts_vars.get('SUPABASE_PROFILES_TABLE', 'profiles'),
        'SUPABASE_SOPS_TABLE': ts_vars.get('SUPABASE_SOPS_TABLE', 'sops'),
        'SUPABASE_SOP_RULES_TABLE': 'sop_rules',
        'SUPABASE_SOP_LOGS_TABLE': 'sop_processing_logs',
        'SUPABASE_FEATURE_FLAGS_TABLE': 'feature_flags',
        'SUPABASE_SOPS_BUCKET': ts_vars.get('SUPABASE_SOPS_BUCKET', 'sops'),
        'SUPABASE_AUDIO_BUCKET': ts_vars.get('SUPABASE_AUDIO_BUCKET', 'audio-files'),
        
        # OpenAI
        'OPENAI_API_KEY': ts_vars.get('OPENAI_API_KEY', ''),
        'OPENAI_ORGANIZATION': ts_vars.get('OPENAI_ORGANIZATION', ''),
        'OPENAI_MAX_RETRIES': ts_vars.get('OPENAI_MAX_RETRIES', '3'),
        'OPENAI_TIMEOUT': ts_vars.get('OPENAI_TIMEOUT', '600000'),
        'OPENAI_TRANSCRIPTION_MODEL': 'gpt-4o-mini-transcribe',
        'OPENAI_TRANSCRIPTION_LANGUAGE': '',
        
        # Anthropic
        'ANTHROPIC_API_KEY': ts_vars.get('ANTHROPIC_API_KEY', ''),
        'ANTHROPIC_MAX_RETRIES': ts_vars.get('ANTHROPIC_MAX_RETRIES', '3'),
        'ANTHROPIC_TIMEOUT': ts_vars.get('ANTHROPIC_TIMEOUT', '600000'),
        
        # AssemblyAI
        'ASSEMBLYAI_API_KEY': ts_vars.get('ASSEMBLYAI_API_KEY', ''),
        'ASSEMBLYAI_PII_REDACTION_ENABLED': ts_vars.get('ASSEMBLYAI_PII_REDACTION_ENABLED', 'false').lower(),
        'ASSEMBLYAI_PII_SUBSTITUTION': ts_vars.get('ASSEMBLYAI_PII_SUBSTITUTION', 'hash'),
        'ASSEMBLYAI_GENERATE_REDACTED_AUDIO': ts_vars.get('ASSEMBLYAI_GENERATE_REDACTED_AUDIO', 'false').lower(),
        
        # LandingAI
        'LANDINGAI_API_KEY': ts_vars.get('LANDINGAI_API_KEY', ''),
        
        # AI Configuration
        'AI_PRIMARY_PROVIDER': ts_vars.get('AI_PRIMARY_PROVIDER', 'openai'),
        'AI_FALLBACK_PROVIDER': ts_vars.get('AI_FALLBACK_PROVIDER', ''),
        'AI_ENABLE_FALLBACK': ts_vars.get('AI_ENABLE_FALLBACK', 'true').lower(),
        
        # SOP Models
        'SOP_STAGE_DISCOVERY_MODEL': ts_vars.get('SOP_STAGE_DISCOVERY_MODEL', 'gpt-5-mini'),
        'SOP_RULE_EXTRACTION_MODEL': ts_vars.get('SOP_RULE_EXTRACTION_MODEL', 'gpt-5-nano'),
        'SOP_EXAMPLE_EXTRACTION_MODEL': ts_vars.get('SOP_EXAMPLE_EXTRACTION_MODEL', 'gpt-5-nano'),
        'SOP_FLOW_EXTRACTION_MODEL': ts_vars.get('SOP_FLOW_EXTRACTION_MODEL', 'gpt-5-mini'),
        'SOP_VALIDATION_MODEL': ts_vars.get('SOP_VALIDATION_MODEL', 'gpt-5-mini'),
        'SOP_FORMATTING_MODEL': ts_vars.get('SOP_FORMATTING_MODEL', 'gpt-5-nano'),
        'SOP_REVIEW_MODEL': ts_vars.get('SOP_REVIEW_MODEL', 'claude-sonnet-4-20250514'),
        'SOP_VISION_MODEL': ts_vars.get('SOP_VISION_MODEL', 'gpt-5'),
        
        # Twilio
        'TWILIO_ACCOUNT_SID': ts_vars.get('TWILIO_ACCOUNT_SID', ''),
        'TWILIO_AUTH_TOKEN': ts_vars.get('TWILIO_AUTH_TOKEN', ''),
        'TWILIO_PHONE_NUMBER': ts_vars.get('TWILIO_PHONE_NUMBER', ''),
        'TWILIO_WEBHOOK_BASE_URL': ts_vars.get('TWILIO_WEBHOOK_BASE_URL', ''),
        'TWILIO_AGENT_NUMBER': ts_vars.get('TWILIO_AGENT_NUMBER', ''),
        'TWILIO_TRANSCRIPTION_PROVIDER': ts_vars.get('TWILIO_TRANSCRIPTION_PROVIDER', 'google'),
        'TWILIO_INTELLIGENCE_SERVICE_SID': ts_vars.get('TWILIO_INTELLIGENCE_SERVICE_SID', ''),
        
        # Cloud Tasks
        'CLOUD_TASKS_ENABLED': 'false',
        'GCP_PROJECT_ID': '',
        'GCP_REGION': '',
        'GCP_TASK_QUEUE_NAME': 'transcription-queue',
        'CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL': '',
        
        # Redis
        'REDIS_URL': 'redis://localhost:6379/0',
        
        # CORS
        'CORS_ALLOWED_ORIGINS': 'http://localhost:3000,http://localhost:5173',
        
        # Logging
        'LOG_LEVEL': ts_vars.get('LOG_LEVEL', 'DEBUG').upper(),
        
        # Asterisk ARI
        'ARI_URL': ts_vars.get('ARI_URL', ''),
        'ARI_USER': ts_vars.get('ARI_USER', ''),
        'ARI_PASSWORD': ts_vars.get('ARI_PASSWORD', ''),
        'ARI_STASIS_APP': ts_vars.get('ARI_STASIS_APP', 'verc-realtime-audio'),
    }
    
    return django_vars

def write_django_env(django_vars):
    """
    Write Django .env file to disk.
    
    Creates a backup of existing .env file if one already exists.
    
    Args:
        django_vars: Dictionary of Django environment variables to write
    """
    if DJANGO_ENV_PATH.exists():
        backup_path = DJANGO_ENV_PATH.with_suffix('.env.backup')
        print(f"Warning: .env file already exists. Backing up to {backup_path}")
        DJANGO_ENV_PATH.rename(backup_path)
    
    with open(DJANGO_ENV_PATH, 'w') as f:
        f.write("# Django Backend Service Environment Variables\n")
        f.write("# Generated from TypeScript backend .env file\n\n")
        
        f.write("# Django Settings\n")
        f.write(f"DJANGO_ENV={django_vars['DJANGO_ENV']}\n")
        f.write(f"SECRET_KEY={django_vars['SECRET_KEY']}\n")
        f.write(f"DEBUG={django_vars['DEBUG']}\n")
        f.write(f"ALLOWED_HOSTS={django_vars['ALLOWED_HOSTS']}\n\n")
        
        f.write("# Server\n")
        f.write(f"API_PORT={django_vars['API_PORT']}\n")
        f.write(f"PORT={django_vars['PORT']}\n\n")
        
        f.write("# Supabase Configuration\n")
        f.write(f"SUPABASE_URL={django_vars['SUPABASE_URL']}\n")
        f.write(f"SUPABASE_ANON_KEY={django_vars['SUPABASE_ANON_KEY']}\n")
        f.write(f"SUPABASE_SERVICE_ROLE_KEY={django_vars['SUPABASE_SERVICE_ROLE_KEY']}\n")
        f.write(f"SUPABASE_TRANSCRIPTIONS_TABLE={django_vars['SUPABASE_TRANSCRIPTIONS_TABLE']}\n")
        f.write(f"SUPABASE_SESSIONS_TABLE={django_vars['SUPABASE_SESSIONS_TABLE']}\n")
        f.write(f"SUPABASE_PROFILES_TABLE={django_vars['SUPABASE_PROFILES_TABLE']}\n")
        f.write(f"SUPABASE_SOPS_TABLE={django_vars['SUPABASE_SOPS_TABLE']}\n")
        f.write(f"SUPABASE_SOP_RULES_TABLE={django_vars['SUPABASE_SOP_RULES_TABLE']}\n")
        f.write(f"SUPABASE_SOP_LOGS_TABLE={django_vars['SUPABASE_SOP_LOGS_TABLE']}\n")
        f.write(f"SUPABASE_FEATURE_FLAGS_TABLE={django_vars['SUPABASE_FEATURE_FLAGS_TABLE']}\n")
        f.write(f"SUPABASE_SOPS_BUCKET={django_vars['SUPABASE_SOPS_BUCKET']}\n")
        f.write(f"SUPABASE_AUDIO_BUCKET={django_vars['SUPABASE_AUDIO_BUCKET']}\n\n")
        
        f.write("# AI Provider API Keys\n")
        f.write(f"OPENAI_API_KEY={django_vars['OPENAI_API_KEY']}\n")
        f.write(f"OPENAI_ORGANIZATION={django_vars['OPENAI_ORGANIZATION']}\n")
        f.write(f"OPENAI_MAX_RETRIES={django_vars['OPENAI_MAX_RETRIES']}\n")
        f.write(f"OPENAI_TIMEOUT={django_vars['OPENAI_TIMEOUT']}\n")
        f.write(f"OPENAI_TRANSCRIPTION_MODEL={django_vars['OPENAI_TRANSCRIPTION_MODEL']}\n")
        f.write(f"OPENAI_TRANSCRIPTION_LANGUAGE={django_vars['OPENAI_TRANSCRIPTION_LANGUAGE']}\n\n")
        
        f.write(f"ANTHROPIC_API_KEY={django_vars['ANTHROPIC_API_KEY']}\n")
        f.write(f"ANTHROPIC_MAX_RETRIES={django_vars['ANTHROPIC_MAX_RETRIES']}\n")
        f.write(f"ANTHROPIC_TIMEOUT={django_vars['ANTHROPIC_TIMEOUT']}\n\n")
        
        f.write(f"ASSEMBLYAI_API_KEY={django_vars['ASSEMBLYAI_API_KEY']}\n")
        f.write(f"ASSEMBLYAI_PII_REDACTION_ENABLED={django_vars['ASSEMBLYAI_PII_REDACTION_ENABLED']}\n")
        f.write(f"ASSEMBLYAI_PII_SUBSTITUTION={django_vars['ASSEMBLYAI_PII_SUBSTITUTION']}\n")
        f.write(f"ASSEMBLYAI_GENERATE_REDACTED_AUDIO={django_vars['ASSEMBLYAI_GENERATE_REDACTED_AUDIO']}\n\n")
        
        f.write(f"LANDINGAI_API_KEY={django_vars['LANDINGAI_API_KEY']}\n\n")
        
        f.write("# AI Provider Configuration\n")
        f.write(f"AI_PRIMARY_PROVIDER={django_vars['AI_PRIMARY_PROVIDER']}\n")
        f.write(f"AI_FALLBACK_PROVIDER={django_vars['AI_FALLBACK_PROVIDER']}\n")
        f.write(f"AI_ENABLE_FALLBACK={django_vars['AI_ENABLE_FALLBACK']}\n\n")
        
        f.write("# Model Configuration\n")
        f.write(f"SOP_STAGE_DISCOVERY_MODEL={django_vars['SOP_STAGE_DISCOVERY_MODEL']}\n")
        f.write(f"SOP_RULE_EXTRACTION_MODEL={django_vars['SOP_RULE_EXTRACTION_MODEL']}\n")
        f.write(f"SOP_EXAMPLE_EXTRACTION_MODEL={django_vars['SOP_EXAMPLE_EXTRACTION_MODEL']}\n")
        f.write(f"SOP_FLOW_EXTRACTION_MODEL={django_vars['SOP_FLOW_EXTRACTION_MODEL']}\n")
        f.write(f"SOP_VALIDATION_MODEL={django_vars['SOP_VALIDATION_MODEL']}\n")
        f.write(f"SOP_FORMATTING_MODEL={django_vars['SOP_FORMATTING_MODEL']}\n")
        f.write(f"SOP_REVIEW_MODEL={django_vars['SOP_REVIEW_MODEL']}\n")
        f.write(f"SOP_VISION_MODEL={django_vars['SOP_VISION_MODEL']}\n\n")
        
        f.write("# Twilio Configuration\n")
        f.write(f"TWILIO_ACCOUNT_SID={django_vars['TWILIO_ACCOUNT_SID']}\n")
        f.write(f"TWILIO_AUTH_TOKEN={django_vars['TWILIO_AUTH_TOKEN']}\n")
        f.write(f"TWILIO_PHONE_NUMBER={django_vars['TWILIO_PHONE_NUMBER']}\n")
        f.write(f"TWILIO_WEBHOOK_BASE_URL={django_vars['TWILIO_WEBHOOK_BASE_URL']}\n")
        f.write(f"TWILIO_AGENT_NUMBER={django_vars['TWILIO_AGENT_NUMBER']}\n")
        f.write(f"TWILIO_TRANSCRIPTION_PROVIDER={django_vars['TWILIO_TRANSCRIPTION_PROVIDER']}\n")
        f.write(f"TWILIO_INTELLIGENCE_SERVICE_SID={django_vars['TWILIO_INTELLIGENCE_SERVICE_SID']}\n\n")
        
        f.write("# Google Cloud Tasks\n")
        f.write(f"CLOUD_TASKS_ENABLED={django_vars['CLOUD_TASKS_ENABLED']}\n")
        f.write(f"GCP_PROJECT_ID={django_vars['GCP_PROJECT_ID']}\n")
        f.write(f"GCP_REGION={django_vars['GCP_REGION']}\n")
        f.write(f"GCP_TASK_QUEUE_NAME={django_vars['GCP_TASK_QUEUE_NAME']}\n")
        f.write(f"CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL={django_vars['CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL']}\n\n")
        
        f.write("# Redis (for Channels/WebSocket)\n")
        f.write(f"REDIS_URL={django_vars['REDIS_URL']}\n\n")
        
        f.write("# CORS\n")
        f.write(f"CORS_ALLOWED_ORIGINS={django_vars['CORS_ALLOWED_ORIGINS']}\n\n")
        
        f.write("# Logging\n")
        f.write(f"LOG_LEVEL={django_vars['LOG_LEVEL']}\n\n")
        
        f.write("# Asterisk ARI (Real-time Audio)\n")
        f.write(f"ARI_URL={django_vars['ARI_URL']}\n")
        f.write(f"ARI_USER={django_vars['ARI_USER']}\n")
        f.write(f"ARI_PASSWORD={django_vars['ARI_PASSWORD']}\n")
        f.write(f"ARI_STASIS_APP={django_vars['ARI_STASIS_APP']}\n")

def main():
    """
    Main function to migrate environment variables from TypeScript to Django format.
    """
    print("Migrating environment variables from TypeScript backend...")
    
    ts_vars = read_ts_env()
    print(f"Read {len(ts_vars)} environment variables from TypeScript .env")
    
    django_vars = create_django_env(ts_vars)
    write_django_env(django_vars)
    
    print(f"Created Django .env file at: {DJANGO_ENV_PATH}")
    print("\nNext steps:")
    print("  1. Review the .env file and update SECRET_KEY for production")
    print("  2. Verify all API keys and configuration values")
    print("  3. Run: python manage.py check")

if __name__ == '__main__':
    main()

