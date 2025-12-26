#!/usr/bin/env python
"""Test Buffalo PBX event parsing logic"""

import asyncio
import sys
import os

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.twilio.pbx_monitor import process_buffalo_event

# Test events
test_events = [
    # OUTBOUND call
    {
        "event": "new",
        "callid": "test-outbound-1",
        "stype": "phone",
        "snumber": "02920997",  # Agent
        "dnumber": "7001234567",  # Customer
        "callername_internal": "Agent Smith"
    },

    # INBOUND call
    {
        "event": "new",
        "callid": "test-inbound-1",
        "stype": "external",
        "cnumber": "7009876543",  # Customer (DID)
        "dnumber": "02920998",  # Agent
        "callername": "Jane Customer"
    },

    # Call answered
    {
        "event": "answered",
        "callid": "test-outbound-1"
    },

    # Call terminated
    {
        "event": "terminated",
        "callid": "test-inbound-1"
    }
]

async def test():
    print("Testing Buffalo PBX event processing...\n")

    for i, event in enumerate(test_events, 1):
        print(f"\n--- Test {i}: {event['event']} ---")
        await process_buffalo_event(event)

    print("\n✅ All tests complete")

if __name__ == '__main__':
    asyncio.run(test())
