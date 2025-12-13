"""
Buffalo PBX WebSocket Monitor
Connects to Buffalo PBX SPOP interface and monitors call events.
"""

import asyncio
import websockets
import json
import logging
from django.conf import settings
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Track calls waiting to be answered
# Key: call_id, Value: call details dict
pending_calls: Dict[str, dict] = {}


async def connect_to_buffalo_pbx():
    """
    Connect to Buffalo PBX WebSocket and monitor call events.

    Maintains persistent connection with automatic reconnection.
    Processes SPOP events: new, ringing, answered, terminated
    """

    # Build WebSocket URL with auth credentials
    username = settings.APP_SETTINGS.buffalo_pbx.username
    password = settings.APP_SETTINGS.buffalo_pbx.password
    wss_url = settings.APP_SETTINGS.buffalo_pbx.wss_url

    if not username or not password:
        logger.error("[PBX-MONITOR] Missing Buffalo PBX credentials in settings")
        return

    # Add credentials as query parameters
    url = f"{wss_url}?username={username}&password={password}"

    retry_count = 0
    max_retries = 999999  # Effectively infinite

    while True:
        try:
            logger.info(f"[PBX-MONITOR] Connecting to Buffalo PBX... (attempt {retry_count + 1})")

            # Connect with ping to keep connection alive
            async with websockets.connect(
                url,
                ping_interval=settings.APP_SETTINGS.buffalo_pbx.ping_interval,
                ping_timeout=settings.APP_SETTINGS.buffalo_pbx.ping_timeout
            ) as ws:
                logger.info("[PBX-MONITOR] ✅ Connected to Buffalo PBX WebSocket")
                retry_count = 0  # Reset on successful connection

                # Listen for messages
                async for message in ws:
                    try:
                        # Parse JSON event
                        event = json.loads(message)
                        await process_buffalo_event(event)
                    except json.JSONDecodeError:
                        logger.debug(f"[PBX-MONITOR] Received non-JSON message: {message[:100]}")
                    except Exception as e:
                        logger.error(f"[PBX-MONITOR] Error processing event: {e}", exc_info=True)

        except websockets.ConnectionClosed:
            logger.warning("[PBX-MONITOR] Connection closed by server, reconnecting...")
        except Exception as e:
            logger.error(f"[PBX-MONITOR] Connection error: {e}", exc_info=True)

        # Exponential backoff with max delay
        retry_count += 1
        wait_time = min(
            2 ** min(retry_count, 6),  # Cap at 2^6 = 64 seconds
            settings.APP_SETTINGS.buffalo_pbx.max_reconnect_delay
        )
        logger.info(f"[PBX-MONITOR] Retrying in {wait_time} seconds...")
        await asyncio.sleep(wait_time)


async def process_buffalo_event(event: dict):
    """
    Process SPOP events from Buffalo PBX.

    Event types:
    - new: New call initiated
    - ringing: Call is ringing
    - answered: Call was answered
    - terminated: Call ended

    Args:
        event: Parsed JSON event from Buffalo PBX
    """

    event_type = event.get('event')
    call_id = event.get('callid') or event.get('uniqueid')

    if not call_id:
        logger.debug(f"[PBX-EVENT] Event without call_id: {event_type}")
        return

    logger.debug(f"[PBX-EVENT] {event_type} - CallId={call_id}")

    # Helper function: Check if number is a DID (7 followed by 9 digits)
    def is_did(num) -> bool:
        if not num:
            return False
        num_str = str(num)
        return num_str.startswith('7') and len(num_str) == 10

    # NEW or RINGING: Track call for potential SPY
    if event_type in ['new', 'ringing']:
        stype = event.get('stype')

        # Determine direction and agent extension
        if stype == 'phone':
            # OUTBOUND: Agent calling out
            # If snumber is DID, agent is dnumber, otherwise agent is snumber
            if is_did(event.get('snumber')):
                agent_ext = event.get('dnumber')
                direction = 'OUTBOUND'
            else:
                agent_ext = event.get('snumber')
                direction = 'OUTBOUND'

        elif stype == 'external':
            # INBOUND: External call coming in
            # If cnumber is DID, agent is dnumber, otherwise agent is cnumber
            if is_did(event.get('cnumber')):
                agent_ext = event.get('dnumber')
                direction = 'INBOUND'
            else:
                agent_ext = event.get('cnumber')
                direction = 'INBOUND'

        elif stype == 'queue':
            # Queue ring - update existing call with actual agent extension
            if call_id in pending_calls and event.get('dnumber'):
                old_ext = pending_calls[call_id].get('spyNumber')
                new_ext = event.get('dnumber')
                pending_calls[call_id]['spyNumber'] = new_ext
                logger.info(f"[PBX-UPDATE] CallId={call_id} - Updated agent {old_ext} → {new_ext}")
            return

        else:
            # Unknown stype, skip
            return

        # Don't spy on our own extension
        if agent_ext == settings.APP_SETTINGS.buffalo_pbx.sip_username:
            logger.debug(f"[PBX-SKIP] Ignoring call to own extension: {agent_ext}")
            return

        # Track call
        if agent_ext:
            pending_calls[call_id] = {
                'spyNumber': agent_ext,
                'direction': direction,
                'caller': event.get('callername_internal', event.get('callername', 'Unknown')),
                'destNum': event.get('dnumber', 'N/A'),
                'callId': call_id,
                'snumber': event.get('snumber'),
                'dnumber': event.get('dnumber'),
                'cnumber': event.get('cnumber'),
            }
            logger.info(
                f"[PBX-TRACK] CallId={call_id} - "
                f"Agent={agent_ext}, Direction={direction}, "
                f"Caller={pending_calls[call_id]['caller']}, Dest={pending_calls[call_id]['destNum']}"
            )

    # ANSWERED: Call was picked up
    elif event_type == 'answered' and call_id in pending_calls:
        call_details = pending_calls[call_id]
        agent_ext = call_details['spyNumber']

        logger.info(
            f"[PBX-ANSWERED] 🎯 CallId={call_id} answered - "
            f"Agent={agent_ext}, Direction={call_details['direction']}"
        )

        # Initiate SPY call via Twilio
        from apps.twilio.services import initiate_spy_call

        result = initiate_spy_call(agent_ext, call_details)

        if result['success']:
            logger.info(
                f"[PBX-ANSWERED] SPY call initiated successfully - "
                f"CallSid={result['call_sid']}, SessionId={result['session_id']}"
            )
        else:
            logger.error(
                f"[PBX-ANSWERED] Failed to initiate SPY call - "
                f"Extension={agent_ext}, Error={result['error']}"
            )

        # Remove from pending (answered calls are now active)
        del pending_calls[call_id]

    # TERMINATED: Call ended
    elif event_type == 'terminated':
        if call_id in pending_calls:
            logger.info(f"[PBX-TERMINATED] CallId={call_id} ended before answer")
            del pending_calls[call_id]
        else:
            logger.debug(f"[PBX-TERMINATED] CallId={call_id} ended")

        # TODO Phase 3: Cleanup SPY call if exists


def run_pbx_monitor():
    """
    Entry point for running PBX monitor.

    This function starts the async event loop and connects to Buffalo PBX.
    Called from Django management command.
    """
    logger.info("[PBX-MONITOR] Starting Buffalo PBX monitor...")
    logger.info(f"[PBX-MONITOR] Connecting to {settings.APP_SETTINGS.buffalo_pbx.wss_url}")

    try:
        asyncio.run(connect_to_buffalo_pbx())
    except KeyboardInterrupt:
        logger.info("[PBX-MONITOR] Shutting down gracefully...")
    except Exception as e:
        logger.error(f"[PBX-MONITOR] Fatal error: {e}", exc_info=True)
        raise
