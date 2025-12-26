#!/usr/bin/env python
"""Test TwiML generation matches Twilio spec"""

from twilio.twiml.voice_response import VoiceResponse

# Generate TwiML exactly as our webhook does
response = VoiceResponse()
response.say("Connecting to monitoring session", voice='alice', language='en-US')
response.pause(length=1800)

xml = str(response)

print("Generated TwiML:")
print(xml)
print(f"\nLength: {len(xml)} bytes")
print(f"Content-Type: text/xml; charset=utf-8")

# Verify structure
assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
assert '<Response>' in xml
assert '<Say' in xml and 'voice="alice"' in xml and 'language="en-US"' in xml
assert 'Connecting to monitoring session' in xml
assert '<Pause length="1800"' in xml
assert '</Response>' in xml

print("\n✅ TwiML validation passed!")
