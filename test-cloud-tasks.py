#!/usr/bin/env python3.12
"""
Test script to verify Cloud Tasks configuration and attempt to queue a test task.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from apps.core.services.cloud_tasks import get_cloud_tasks_client, enqueue_transcription_task

print("=" * 60)
print("Testing Cloud Tasks Configuration")
print("=" * 60)

config = settings.APP_SETTINGS.cloud_tasks

print(f"\n1. Configuration Check:")
print(f"   Enabled: {config.enabled}")
print(f"   Project ID: {config.project_id or '(not set)'}")
print(f"   Region: {config.region or '(not set)'}")
print(f"   Queue Name: {config.queue_name or '(not set)'}")
print(f"   Service Account: {config.service_account_email or '(not set)'}")

if not config.enabled:
    print("\n❌ Cloud Tasks is DISABLED")
    print("   Set CLOUD_TASKS_ENABLED=true in your .env file")
    sys.exit(1)

if not config.project_id or not config.region or not config.queue_name:
    print("\n❌ Cloud Tasks configuration is INCOMPLETE")
    print("   Required environment variables:")
    print("   - GCP_PROJECT_ID")
    print("   - GCP_REGION")
    print("   - GCP_TASK_QUEUE_NAME")
    sys.exit(1)

print("\n2. Testing Cloud Tasks Client...")
client = get_cloud_tasks_client()

if not client:
    print("❌ Failed to create Cloud Tasks client")
    print("   Check your GCP authentication and permissions")
    sys.exit(1)

print("✓ Cloud Tasks client created successfully")

print("\n3. Testing Task Queueing...")
import uuid
test_session_id = str(uuid.uuid4())
test_storage_path = "test/audio.wav"

# Get service URL
service_url = os.getenv('CLOUD_RUN_SERVICE_URL', 'https://verc-app-staging-clw2hnetfa-uk.a.run.app')
print(f"   Service URL: {service_url}")

try:
    success = enqueue_transcription_task(
        session_id=test_session_id,
        storage_path=test_storage_path,
        service_url=service_url
    )
    
    if success:
        print(f"✓ Test task queued successfully!")
        print(f"   Session ID: {test_session_id}")
        print(f"   Check Cloud Tasks console for the queued task")
    else:
        print("❌ Failed to queue test task")
        print("   Check the logs above for error details")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Error queueing task: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("Test Complete")
print("=" * 60)

