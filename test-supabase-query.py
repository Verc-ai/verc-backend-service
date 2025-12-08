#!/usr/bin/env python3
"""
Test script to verify Supabase connectivity and check for sessions.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.core.services.supabase import get_supabase_client
from django.conf import settings

print("=" * 60)
print("Testing Supabase Connection")
print("=" * 60)

# Check configuration
config = settings.APP_SETTINGS.supabase
print(f"\n1. Configuration Check:")
print(f"   URL: {'✓ Set' if config.url else '✗ Missing'}")
print(f"   Service Role Key: {'✓ Set' if config.service_role_key else '✗ Missing'}")
print(f"   URL Value: {config.url[:50] if config.url else 'None'}...")

if not config.url or not config.service_role_key:
    print("\n❌ Supabase not configured! Check your .env file.")
    sys.exit(1)

# Get client
print(f"\n2. Creating Supabase client...")
supabase = get_supabase_client()

if not supabase:
    print("❌ Failed to create Supabase client")
    sys.exit(1)

print("✓ Supabase client created")

# Test query
print(f"\n3. Testing query...")
try:
    response = supabase.table('transcription_sessions').select('id', count='exact').limit(5).execute()
    
    print(f"✓ Query successful")
    print(f"   Total sessions in database: {response.count if hasattr(response, 'count') else 'unknown'}")
    print(f"   Sample session IDs:")
    for i, row in enumerate(response.data[:5], 1):
        print(f"      {i}. {row.get('id', 'N/A')}")
    
    if response.count == 0:
        print("\n⚠️  No sessions found in database.")
        print("   This could mean:")
        print("   - The table is empty")
        print("   - You need to create some test data")
        print("   - The table name might be different")
    else:
        print(f"\n✓ Found {response.count} sessions in database")
        
except Exception as e:
    print(f"❌ Query failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("Test Complete")
print("=" * 60)

