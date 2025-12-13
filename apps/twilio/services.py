"""
Twilio service functions for SPY call management.
"""
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from django.conf import settings
from apps.core.services.supabase import get_supabase_client
import logging

logger = logging.getLogger(__name__)


def initiate_spy_call(extension: str, call_details: dict) -> dict:
    """
    Initiate a Twilio SPY call to monitor a Buffalo PBX call.

    Args:
        extension: Agent extension to spy on (e.g., "6190")
        call_details: Dict with call metadata from PBX event:
            - callId: Buffalo PBX call ID
            - direction: INBOUND or OUTBOUND
            - caller: Caller name/number
            - destNum: Destination number
            - spyNumber: Extension being monitored

    Returns:
        Dict with:
            - success: bool
            - call_sid: Twilio call SID (if successful)
            - session_id: Database session ID (if successful)
            - error: Error message (if failed)
    """

    # Build SIP URI: sip:*44{extension}@{host}:{port}
    sip_uri = (
        f"sip:*44{extension}@"
        f"{settings.APP_SETTINGS.buffalo_pbx.sip_host}:"
        f"{settings.APP_SETTINGS.buffalo_pbx.sip_port}"
    )

    # Get base URL for webhooks
    base_url = settings.APP_SETTINGS.twilio.webhook_base_url

    # Voice webhook URL (Phase 1B endpoint)
    voice_url = f"{base_url}/api/twilio/voice/"

    # Status callback URLs
    status_callback_url = f"{base_url}/api/twilio/call-status/"
    recording_status_callback_url = f"{base_url}/api/twilio/recording/"

    try:
        # Initialize Twilio client
        client = Client(
            settings.APP_SETTINGS.twilio.account_sid,
            settings.APP_SETTINGS.twilio.auth_token
        )

        logger.info(
            f"[SPY-CALL] Initiating SPY call - "
            f"Extension={extension}, BuffaloCallId={call_details['callId']}, "
            f"Direction={call_details['direction']}"
        )

        # Create Twilio call with recording
        call = client.calls.create(
            to=sip_uri,
            from_=settings.APP_SETTINGS.twilio.phone_number,
            url=voice_url,
            status_callback=status_callback_url,
            status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
            status_callback_method='POST',
            record=True,
            recording_channels='dual',
            recording_status_callback=recording_status_callback_url,
            recording_status_callback_method='POST',
            method='POST',
            timeout=30
        )

        call_sid = call.sid

        logger.info(
            f"[SPY-CALL] ✅ Twilio call created - "
            f"CallSid={call_sid}, SIP={sip_uri}"
        )

        # Create session record in Supabase
        supabase = get_supabase_client()

        session_data = {
            'call_sid': call_sid,
            'buffalo_call_id': call_details['callId'],
            'agent_extension': extension,
            'direction': call_details['direction'],
            'caller_info': call_details['caller'],
            'destination_number': call_details['destNum'],
            'status': 'initiated',
            'duration': 0  # Will be updated when call completes
        }

        result = supabase.table('transcription_sessions').insert(session_data).execute()

        if result.data:
            session_id = result.data[0]['id']
            logger.info(
                f"[SPY-CALL] Session created - "
                f"SessionId={session_id}, CallSid={call_sid}"
            )

            return {
                'success': True,
                'call_sid': call_sid,
                'session_id': session_id
            }
        else:
            logger.error(f"[SPY-CALL] Failed to create session record for CallSid={call_sid}")
            return {
                'success': False,
                'error': 'Failed to create session record'
            }

    except TwilioRestException as e:
        logger.error(
            f"[SPY-CALL] Twilio API error - "
            f"Extension={extension}, Error={e.msg}, Code={e.code}"
        )
        return {
            'success': False,
            'error': f"Twilio error: {e.msg}"
        }

    except Exception as e:
        logger.error(
            f"[SPY-CALL] Unexpected error - "
            f"Extension={extension}, Error={str(e)}",
            exc_info=True
        )
        return {
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }
