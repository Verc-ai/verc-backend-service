"""
Twilio service functions for SPY call management.
"""
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from django.conf import settings
from apps.core.services.supabase import get_supabase_client
import logging
import httpx

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


def download_twilio_recording(recording_sid: str, recording_url: str) -> dict:
    """
    Download recording audio from Twilio.

    Args:
        recording_sid: Twilio recording SID
        recording_url: Twilio recording URL (from webhook)

    Returns:
        Dict with:
            - success: bool
            - audio_bytes: Recording audio data (if successful)
            - content_type: Audio MIME type (if successful)
            - error: Error message (if failed)
    """

    try:
        # Initialize Twilio client
        client = Client(
            settings.APP_SETTINGS.twilio.account_sid,
            settings.APP_SETTINGS.twilio.auth_token
        )

        logger.info(
            f"[RECORDING-DOWNLOAD] Downloading recording - RecordingSid={recording_sid}"
        )

        # Fetch recording metadata
        recording = client.recordings(recording_sid).fetch()

        # Build download URL with .wav format for best quality
        # Twilio format: https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Recordings/{RecordingSid}.wav
        download_url = f"https://api.twilio.com{recording.uri.replace('.json', '.wav')}"

        logger.info(
            f"[RECORDING-DOWNLOAD] Fetching audio from Twilio - URL={download_url[:80]}..."
        )

        # Download audio using Twilio credentials for HTTP basic auth
        auth = (settings.APP_SETTINGS.twilio.account_sid, settings.APP_SETTINGS.twilio.auth_token)

        response = httpx.get(download_url, auth=auth, timeout=120.0)
        response.raise_for_status()

        audio_bytes = response.content
        content_type = response.headers.get('Content-Type', 'audio/wav')

        logger.info(
            f"[RECORDING-DOWNLOAD] ✅ Downloaded recording - "
            f"RecordingSid={recording_sid}, Size={len(audio_bytes)} bytes, "
            f"ContentType={content_type}"
        )

        return {
            'success': True,
            'audio_bytes': audio_bytes,
            'content_type': content_type
        }

    except TwilioRestException as e:
        logger.error(
            f"[RECORDING-DOWNLOAD] Twilio API error - "
            f"RecordingSid={recording_sid}, Error={e.msg}, Code={e.code}"
        )
        return {
            'success': False,
            'error': f"Twilio error: {e.msg}"
        }

    except Exception as e:
        logger.error(
            f"[RECORDING-DOWNLOAD] Unexpected error - "
            f"RecordingSid={recording_sid}, Error={str(e)}",
            exc_info=True
        )
        return {
            'success': False,
            'error': f"Download failed: {str(e)}"
        }


def upload_recording_to_storage(
    session_id: int,
    recording_sid: str,
    audio_bytes: bytes,
    content_type: str
) -> dict:
    """
    Upload recording audio to Supabase Storage.

    Args:
        session_id: Transcription session ID
        recording_sid: Twilio recording SID
        audio_bytes: Audio file bytes
        content_type: Audio MIME type (e.g., 'audio/wav')

    Returns:
        Dict with:
            - success: bool
            - storage_path: Path in Supabase Storage (if successful)
            - error: Error message (if failed)
    """

    try:
        supabase = get_supabase_client()
        if not supabase:
            return {
                'success': False,
                'error': 'Supabase client not available'
            }

        config = settings.APP_SETTINGS.supabase
        bucket = config.audio_bucket

        # Generate storage path: twilio-recordings/{session_id}/{recording_sid}.wav
        # This matches the pattern used in existing transcription pipeline
        storage_path = f"twilio-recordings/{session_id}/{recording_sid}.wav"

        logger.info(
            f"[RECORDING-UPLOAD] Uploading to Supabase Storage - "
            f"Bucket={bucket}, Path={storage_path}, Size={len(audio_bytes)} bytes"
        )

        # Upload to Supabase Storage
        # Supabase Python SDK: storage.from_(bucket).upload(path, file)
        result = supabase.storage.from_(bucket).upload(
            path=storage_path,
            file=audio_bytes,
            file_options={
                'content-type': content_type,
                'upsert': 'true'  # Allow overwrite if exists
            }
        )

        # Check for errors
        if hasattr(result, 'error') and result.error:
            raise Exception(f"Storage upload failed: {result.error}")

        logger.info(
            f"[RECORDING-UPLOAD] ✅ Uploaded to storage - "
            f"SessionId={session_id}, Path={storage_path}"
        )

        return {
            'success': True,
            'storage_path': storage_path
        }

    except Exception as e:
        logger.error(
            f"[RECORDING-UPLOAD] Upload failed - "
            f"SessionId={session_id}, RecordingSid={recording_sid}, Error={str(e)}",
            exc_info=True
        )
        return {
            'success': False,
            'error': f"Upload failed: {str(e)}"
        }


def hangup_call(call_sid: str, reason: str = "Hangup requested") -> dict:
    """
    Terminate an active Twilio call.

    Args:
        call_sid: Twilio call SID to terminate
        reason: Reason for hangup (for logging)

    Returns:
        Dict with:
            - success: bool
            - message: Status message (if successful)
            - error: Error message (if failed)
    """

    try:
        # Initialize Twilio client
        client = Client(
            settings.APP_SETTINGS.twilio.account_sid,
            settings.APP_SETTINGS.twilio.auth_token
        )

        logger.info(
            f"[HANGUP-SERVICE] Terminating call - CallSid={call_sid}, Reason={reason}"
        )

        # Update call status to 'completed' to terminate it
        # Twilio API: calls(call_sid).update(status='completed')
        call = client.calls(call_sid).update(status='completed')

        logger.info(
            f"[HANGUP-SERVICE] ✅ Call terminated - "
            f"CallSid={call_sid}, FinalStatus={call.status}"
        )

        return {
            'success': True,
            'message': f'Call terminated: {call.status}'
        }

    except TwilioRestException as e:
        logger.error(
            f"[HANGUP-SERVICE] Twilio API error - "
            f"CallSid={call_sid}, Error={e.msg}, Code={e.code}"
        )

        # Handle specific error codes
        if e.code == 20404:
            # Call not found - may have already ended
            return {
                'success': True,  # Not really an error
                'message': 'Call already ended or not found'
            }

        return {
            'success': False,
            'error': f"Twilio error: {e.msg}"
        }

    except Exception as e:
        logger.error(
            f"[HANGUP-SERVICE] Unexpected error - "
            f"CallSid={call_sid}, Error={str(e)}",
            exc_info=True
        )
        return {
            'success': False,
            'error': f"Hangup failed: {str(e)}"
        }
