"""
Buffalo PBX WebSocket Monitor
Connects to Buffalo PBX SPOP interface and monitors call events.
"""

import asyncio
import websockets
import json
import logging
import signal
import time
from django.conf import settings
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Track calls waiting to be answered
# Key: call_id, Value: call details dict
pending_calls: Dict[str, dict] = {}

# Track answered calls to prevent duplicate SPY call creation
# Buffalo PBX sometimes sends duplicate "answered" events
processed_answered_calls: set = set()


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
        # Check if we've already processed this answered event (duplicate prevention)
        if call_id in processed_answered_calls:
            logger.debug(
                f"[PBX-ANSWERED] Already processed {call_id}, skipping duplicate"
            )
            return

        # Mark as processed to prevent duplicate SPY calls
        processed_answered_calls.add(call_id)

        call_details = pending_calls[call_id]
        agent_ext = call_details['spyNumber']

        logger.info(
            f"[PBX-ANSWERED] 🎯 CallId={call_id} answered - "
            f"Agent={agent_ext}, Direction={call_details['direction']}"
        )

        # Enqueue SPY call initiation via Cloud Tasks (non-blocking)
        from apps.core.services.cloud_tasks import enqueue_start_spy_call_task
        import os

        # Get service URL from environment
        service_url = os.getenv('CLOUD_RUN_SERVICE_URL')
        if not service_url:
            # Fallback for local development or staging
            k_service = os.getenv('K_SERVICE')
            if k_service:
                service_url = 'https://verc-app-staging-clw2hnetfa-uk.a.run.app'
            else:
                # Local development
                service_url = os.getenv('WEBHOOK_BASE_URL', 'http://localhost:8080')

        task_queued = enqueue_start_spy_call_task(agent_ext, call_details, service_url)

        if task_queued:
            logger.info(
                f"[PBX-ANSWERED] ✅ SPY call task enqueued - "
                f"Extension={agent_ext}, BuffaloCallId={call_id}"
            )
        else:
            logger.warning(
                f"[PBX-ANSWERED] ⚠️ Failed to enqueue SPY call task (Cloud Tasks not available) - "
                f"Extension={agent_ext}, BuffaloCallId={call_id}"
            )
            # Fallback: Try direct call if Cloud Tasks is not available
            from apps.twilio.services import initiate_spy_call
            result = initiate_spy_call(agent_ext, call_details)
            if result['success']:
                logger.info(
                    f"[PBX-ANSWERED] ✅ SPY call initiated directly (fallback) - "
                    f"CallSid={result['call_sid']}, SessionId={result['session_id']}"
                )
            else:
                logger.error(
                    f"[PBX-ANSWERED] ❌ Failed to initiate SPY call - "
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

        # Remove from processed set to allow cleanup
        processed_answered_calls.discard(call_id)

        # Enqueue cleanup task via Cloud Tasks (non-blocking)
        from apps.core.services.cloud_tasks import enqueue_cleanup_spy_call_task
        import os

        # Get service URL from environment
        service_url = os.getenv('CLOUD_RUN_SERVICE_URL')
        if not service_url:
            # Fallback for local development or staging
            k_service = os.getenv('K_SERVICE')
            if k_service:
                service_url = 'https://verc-app-staging-clw2hnetfa-uk.a.run.app'
            else:
                # Local development
                service_url = os.getenv('WEBHOOK_BASE_URL', 'http://localhost:8080')

        task_queued = enqueue_cleanup_spy_call_task(call_id, service_url)

        if task_queued:
            logger.info(
                f"[PBX-TERMINATED] ✅ Cleanup task enqueued - BuffaloCallId={call_id}"
            )
        else:
            logger.warning(
                f"[PBX-TERMINATED] ⚠️ Failed to enqueue cleanup task (Cloud Tasks not available) - "
                f"BuffaloCallId={call_id}"
            )
            # Fallback: Try direct cleanup if Cloud Tasks is not available
            await cleanup_spy_call(call_id)


async def cleanup_spy_call(buffalo_call_id: str):
    """
    Terminate SPY call when Buffalo PBX call ends.

    Args:
        buffalo_call_id: Buffalo PBX call ID (used to find session)
    """
    try:
        from apps.core.services.supabase import get_supabase_client
        from django.conf import settings

        supabase = get_supabase_client()
        if not supabase:
            logger.warning(f"[PBX-CLEANUP] Supabase not available for cleanup")
            return

        config = settings.APP_SETTINGS.supabase
        sessions_table = config.sessions_table

        # Find session by buffalo_call_id
        result = supabase.table(sessions_table).select('id, call_sid, status').eq('buffalo_call_id', buffalo_call_id).execute()

        if not result.data or len(result.data) == 0:
            logger.debug(f"[PBX-CLEANUP] No SPY call found for BuffaloCallId={buffalo_call_id}")
            return

        session_data = result.data[0]
        session_id = session_data['id']
        call_sid = session_data.get('call_sid')
        status = session_data.get('status')

        if not call_sid:
            logger.debug(f"[PBX-CLEANUP] Session {session_id} has no call_sid")
            return

        # Only cleanup if call is still active
        if status not in ['initiated', 'calling', 'in_progress']:
            logger.debug(
                f"[PBX-CLEANUP] Session {session_id} already in terminal status: {status}"
            )
            return

        logger.info(
            f"[PBX-CLEANUP] Terminating SPY call - "
            f"SessionId={session_id}, CallSid={call_sid}, BuffaloCallId={buffalo_call_id}"
        )

        # Hangup the SPY call
        from apps.twilio.services import hangup_call

        result = hangup_call(call_sid, reason="Buffalo PBX call terminated")

        if result['success']:
            logger.info(
                f"[PBX-CLEANUP] ✅ SPY call terminated - "
                f"SessionId={session_id}, CallSid={call_sid}"
            )
        else:
            logger.warning(
                f"[PBX-CLEANUP] Failed to terminate SPY call - "
                f"SessionId={session_id}, Error={result['error']}"
            )

    except Exception as e:
        logger.error(
            f"[PBX-CLEANUP] Error cleaning up SPY call - "
            f"BuffaloCallId={buffalo_call_id}, Error={str(e)}",
            exc_info=True
        )


def handle_shutdown(signum, frame):
    """
    Handle SIGTERM and SIGINT signals for graceful shutdown.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    logger.info(f"[PBX-MONITOR] Received signal {signum}, initiating shutdown...")
    raise KeyboardInterrupt


def run_pbx_monitor():
    """
    Entry point for running PBX monitor with feature flag control.

    This function runs an outer control loop that checks the 'pbx-monitor'
    feature flag every 30 seconds. When enabled, it starts the PBX monitor.
    When disabled, it waits and checks again.

    The monitor automatically handles:
    - Feature flag toggling (checks every 30s)
    - Graceful shutdown via SIGTERM/SIGINT
    - Automatic restart on crashes
    - Clean WebSocket reconnection

    Called from Django management command.
    """
    logger.info("[PBX-MONITOR] Starting Buffalo PBX monitor with feature flag control...")
    logger.info(f"[PBX-MONITOR] Target: {settings.APP_SETTINGS.buffalo_pbx.wss_url}")

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    logger.info("[PBX-MONITOR] Registered SIGTERM and SIGINT handlers")

    # Outer control loop - checks feature flag every 30 seconds
    while True:
        try:
            # Check if PBX monitor is enabled via feature flag
            from apps.feature_flags.services import is_feature_enabled

            if is_feature_enabled('pbx-monitor', default=True):
                logger.info("[PBX-MONITOR] ✅ Feature flag enabled, starting monitor...")

                try:
                    # Start the monitor (blocking until error or shutdown)
                    asyncio.run(connect_to_buffalo_pbx())
                except KeyboardInterrupt:
                    logger.info("[PBX-MONITOR] Shutdown signal received, exiting...")
                    break
                except Exception as e:
                    logger.error(
                        f"[PBX-MONITOR] Monitor crashed with error: {e}",
                        exc_info=True
                    )
                    logger.info("[PBX-MONITOR] Will restart after 30 second delay...")

            else:
                logger.info("[PBX-MONITOR] ⏸️  Feature flag disabled, monitor paused")

            # Wait 30 seconds before checking flag again
            logger.debug("[PBX-MONITOR] Sleeping 30 seconds before next flag check...")
            time.sleep(30)

        except KeyboardInterrupt:
            logger.info("[PBX-MONITOR] Shutdown signal during control loop, exiting...")
            break
        except Exception as e:
            logger.error(
                f"[PBX-MONITOR] Unexpected error in control loop: {e}",
                exc_info=True
            )
            logger.info("[PBX-MONITOR] Will retry after 30 second delay...")
            time.sleep(30)

    logger.info("[PBX-MONITOR] Monitor stopped")
