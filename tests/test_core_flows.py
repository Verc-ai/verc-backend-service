#!/usr/bin/env python
"""
Smoke test for 3 core flows (end-to-end):
1. Create Call
2. Create Transcript linked to call
3. Create TranscriptEvent linked to transcript

Pass criteria:
- No FK failures
- No missing indexes causing obvious slowness
- Timestamps populate correctly (created_at/updated_at)
- Any "company_id required" rule works the way you expect
"""

import os
import sys
import django
from datetime import datetime, timezone

# Setup Django
# Add parent directory to path so we can import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.core.models import Company, Call, Transcript, TranscriptEvent
from django.contrib.auth.models import User
import time

def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def test_create_call():
    """Test 1: Create Call"""
    print_section("TEST 1: Create Call")
    
    # Get or create a company (required FK)
    company, created = Company.objects.get_or_create(
        slug='test-company-smoke-test',
        defaults={
            'name': 'Test Company for Smoke Test',
        }
    )
    if created:
        print(f"✓ Created test company: {company.id} ({company.name})")
    else:
        print(f"✓ Using existing company: {company.id} ({company.name})")
    
    # User is optional - set to None since user_id might be UUID in DB but Django User uses integer ID
    # This tests the FK constraint while avoiding type mismatch issues
    user = None
    
    # Create Call
    call_data = {
        'company': company,
        'user': user,  # Optional FK - can be None
        'call_sid': f'TEST_{int(time.time())}',
        'caller_number': '+1234567890',
        'destination_number': '+0987654321',
        'direction': 'inbound',
        'caller_info': 'Test Caller',
        'filename': 'test_call.wav',
        'call_started_at': datetime.now(timezone.utc),
        'metadata': {'test': True, 'smoke_test': True}
    }
    
    try:
        start_time = time.time()
        call = Call.objects.create(**call_data)
        creation_time = time.time() - start_time
        
        # Verify timestamps
        assert call.created_at is not None, "created_at should be populated"
        assert call.updated_at is not None, "updated_at should be populated"
        # Allow small difference (microseconds) - they're set at nearly the same time
        time_diff = abs((call.updated_at - call.created_at).total_seconds())
        assert time_diff < 1.0, f"created_at and updated_at should be close on creation (diff: {time_diff}s)"
        
        print(f"✓ Call created successfully!")
        print(f"  ID: {call.id}")
        print(f"  Company ID: {call.company_id}")
        print(f"  Call SID: {call.call_sid}")
        print(f"  Created at: {call.created_at}")
        print(f"  Updated at: {call.updated_at}")
        print(f"  Creation time: {creation_time:.3f}s")
        
        if creation_time > 1.0:
            print(f"  ⚠ WARNING: Creation took {creation_time:.3f}s (might indicate missing index)")
        
        return call, company, user
        
    except Exception as e:
        print(f"✗ Failed to create Call: {e}")
        raise

def test_create_transcript(call, company, user):
    """Test 2: Create Transcript linked to call"""
    print_section("TEST 2: Create Transcript linked to Call")
    
    transcript_data = {
        'call': call,
        'company': company,
        'user': user,  # Optional FK - can be None
        'transcription_type': 'test_transcription',
        'transcript': 'This is a test transcript for smoke testing.',
        'segments': [{'start': 0, 'end': 5, 'text': 'Hello'}],
        'speaker_count': 2,
        'status': 'completed',
        'transcript_platform': 'test',
        'transcript_model': 'test-model-v1',
    }
    
    try:
        start_time = time.time()
        transcript = Transcript.objects.create(**transcript_data)
        creation_time = time.time() - start_time
        
        # Verify timestamps
        assert transcript.created_at is not None, "created_at should be populated"
        assert transcript.updated_at is not None, "updated_at should be populated"
        # Allow small difference (microseconds) - they're set at nearly the same time
        time_diff = abs((transcript.updated_at - transcript.created_at).total_seconds())
        assert time_diff < 1.0, f"created_at and updated_at should be close on creation (diff: {time_diff}s)"
        
        # Verify FK relationships
        assert transcript.call_id == call.id, "transcript.call_id should match call.id"
        assert transcript.company_id == company.id, "transcript.company_id should match company.id"
        
        print(f"✓ Transcript created successfully!")
        print(f"  ID: {transcript.id}")
        print(f"  Call ID: {transcript.call_id}")
        print(f"  Company ID: {transcript.company_id}")
        print(f"  Created at: {transcript.created_at}")
        print(f"  Updated at: {transcript.updated_at}")
        print(f"  Creation time: {creation_time:.3f}s")
        
        if creation_time > 1.0:
            print(f"  ⚠ WARNING: Creation took {creation_time:.3f}s (might indicate missing index)")
        
        return transcript
        
    except Exception as e:
        print(f"✗ Failed to create Transcript: {e}")
        raise

def test_create_transcript_event(transcript, call, company, user):
    """Test 3: Create TranscriptEvent linked to transcript"""
    print_section("TEST 3: Create TranscriptEvent linked to Transcript")
    
    event_data = {
        'transcript': transcript,
        'call': call,
        'company': company,
        'user': user,  # Optional FK - can be None
        'sequence_number': 1,
        'timestamp_ms': int(time.time() * 1000),
        'speaker': 'Agent',
        'text_chunk': 'Hello, how can I help you today?',
        'pii_redacted': False,
        'sentiment_score': 0.8,
        'is_final': True,
        'payload': {
            'test': True,
            'smoke_test': True,
            'metadata': {'key': 'value'}
        }
    }
    
    try:
        start_time = time.time()
        event = TranscriptEvent.objects.create(**event_data)
        creation_time = time.time() - start_time
        
        # Verify timestamps
        assert event.created_at is not None, "created_at should be populated"
        # Note: transcript_events table doesn't have updated_at column in the database
        # Only verify created_at exists
        
        # Verify FK relationships
        assert event.transcript_id == transcript.id, "event.transcript_id should match transcript.id"
        assert event.call_id == call.id, "event.call_id should match call.id"
        assert event.company_id == company.id, "event.company_id should match company.id"
        
        print(f"✓ TranscriptEvent created successfully!")
        print(f"  ID: {event.id}")
        print(f"  Transcript ID: {event.transcript_id}")
        print(f"  Call ID: {event.call_id}")
        print(f"  Company ID: {event.company_id}")
        print(f"  Sequence: {event.sequence_number}")
        print(f"  Created at: {event.created_at}")
        # Note: transcript_events table doesn't have updated_at column
        print(f"  Creation time: {creation_time:.3f}s")
        
        if creation_time > 1.0:
            print(f"  ⚠ WARNING: Creation took {creation_time:.3f}s (might indicate missing index)")
        
        return event
        
    except Exception as e:
        print(f"✗ Failed to create TranscriptEvent: {e}")
        raise

def test_company_id_requirement():
    """Test 4: Verify company_id is required"""
    print_section("TEST 4: Verify company_id requirement")
    
    # Try to create Call without company_id
    try:
        call = Call.objects.create(
            call_sid='TEST_NO_COMPANY',
            caller_number='+1234567890',
        )
        print("✗ ERROR: Call was created without company_id (should have failed!)")
        call.delete()  # Cleanup
        return False
    except Exception as e:
        if 'company' in str(e).lower() or 'company_id' in str(e).lower() or 'not null' in str(e).lower():
            print(f"✓ Correctly rejected Call creation without company_id: {type(e).__name__}")
            return True
        else:
            print(f"✗ Unexpected error when creating Call without company_id: {e}")
            return False

def test_timestamp_updates():
    """Test 5: Verify updated_at changes on update"""
    print_section("TEST 5: Verify updated_at changes on update")
    
    try:
        # Get the test company
        company = Company.objects.get(slug='test-company-smoke-test')
        
        # Create a call (user is optional)
        call = Call.objects.create(
            company=company,
            user=None,  # Optional FK
            call_sid=f'TEST_UPDATE_{int(time.time())}',
        )
        
        original_updated_at = call.updated_at
        print(f"  Original updated_at: {original_updated_at}")
        
        # Wait a moment to ensure timestamp difference
        time.sleep(0.1)
        
        # Update the call
        call.metadata = {'updated': True}
        call.save()
        
        call.refresh_from_db()
        new_updated_at = call.updated_at
        print(f"  New updated_at: {new_updated_at}")
        
        if new_updated_at > original_updated_at:
            print("✓ updated_at correctly changed after update")
            call.delete()  # Cleanup
            return True
        else:
            print("✗ ERROR: updated_at did not change after update")
            call.delete()  # Cleanup
            return False
            
    except Exception as e:
        print(f"✗ Failed to test timestamp updates: {e}")
        return False

def cleanup_test_data():
    """Clean up test data"""
    print_section("Cleanup: Removing test data")
    
    try:
        # Delete test transcript events
        TranscriptEvent.objects.filter(
            call__call_sid__startswith='TEST_'
        ).delete()
        print("✓ Deleted test TranscriptEvents")
        
        # Delete test transcripts
        Transcript.objects.filter(
            call__call_sid__startswith='TEST_'
        ).delete()
        print("✓ Deleted test Transcripts")
        
        # Delete test calls
        Call.objects.filter(
            call_sid__startswith='TEST_'
        ).delete()
        print("✓ Deleted test Calls")
        
        # Optionally delete test company (commented out to preserve for future tests)
        # company = Company.objects.filter(slug='test-company-smoke-test').first()
        # if company:
        #     company.delete()
        #     print("✓ Deleted test Company")
        
    except Exception as e:
        print(f"⚠ Warning during cleanup: {e}")

def main():
    """Run all smoke tests"""
    print("\n" + "=" * 60)
    print("  SMOKE TEST: Core Flows (Call → Transcript → TranscriptEvent)")
    print("=" * 60)
    
    results = {
        'call_creation': False,
        'transcript_creation': False,
        'event_creation': False,
        'company_id_required': False,
        'timestamp_updates': False,
    }
    
    call = None
    transcript = None
    event = None
    company = None
    user = None
    
    try:
        # Test 1: Create Call
        call, company, user = test_create_call()
        results['call_creation'] = True
        
        # Test 2: Create Transcript
        transcript = test_create_transcript(call, company, user)
        results['transcript_creation'] = True
        
        # Test 3: Create TranscriptEvent
        event = test_create_transcript_event(transcript, call, company, user)
        results['event_creation'] = True
        
        # Test 4: Verify company_id requirement
        results['company_id_required'] = test_company_id_requirement()
        
        # Test 5: Verify timestamp updates
        results['timestamp_updates'] = test_timestamp_updates()
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    # Print summary
    print_section("Test Summary")
    
    all_passed = all(results.values())
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    if all_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Some tests failed")
    
    # Cleanup
    cleanup_test_data()
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())

