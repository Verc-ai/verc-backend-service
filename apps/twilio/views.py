"""
Twilio webhook views.
"""
from django.http import HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from twilio.twiml.voice_response import VoiceResponse
from apps.core.services.supabase import get_supabase_client
import logging

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class VoiceWebhookView(View):
    """
    POST /api/twilio/voice
    Handle incoming SPY call - returns TwiML to keep call alive and enable recording.

    This endpoint is called by Twilio when a SPY call is initiated.
    We return TwiML that:
    1. Announces connection established
    2. Pauses for 30 minutes (keeping call active for recording)
    3. Recording is automatically enabled via call.create() parameters

    Twilio sends these parameters via POST:
    - CallSid: Unique call identifier
    - CallStatus: Current call status (initiated, ringing, in-progress, etc.)
    - From: Caller number
    - To: Destination (SIP URI for SPY calls)
    """

    def post(self, request):
        # Extract Twilio webhook parameters
        call_sid = request.POST.get('CallSid', 'unknown')
        call_status = request.POST.get('CallStatus', 'unknown')
        from_number = request.POST.get('From', 'unknown')
        to_number = request.POST.get('To', 'unknown')

        logger.info(
            f"[TWILIO-VOICE] Webhook called - "
            f"CallSid={call_sid}, Status={call_status}, "
            f"From={from_number}, To={to_number}"
        )

        # Generate TwiML response
        response = VoiceResponse()

        # Announce connection (voice='alice' for natural speech)
        response.say(
            "Connecting to monitoring session",
            voice='alice',
            language='en-US'
        )

        # Pause for 30 minutes (1800 seconds)
        # This keeps the call alive while the SPY session is active
        # Call will automatically end when original Buffalo call terminates
        response.pause(length=1800)

        logger.info(
            f"[TWILIO-VOICE] Returning TwiML - "
            f"CallSid={call_sid}, TwiML length={len(str(response))} bytes"
        )

        # Return TwiML as XML with proper content type
        return HttpResponse(
            str(response),
            content_type='text/xml; charset=utf-8'
        )


class CallStatusView(APIView):
    """
    POST /api/twilio/call-status
    Handle call status updates.
    """
    def post(self, request):
        # TODO: Implement call status webhook
        return Response({'message': 'Call status webhook - to be implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED)


@method_decorator(csrf_exempt, name='dispatch')
class RecordingView(APIView):
    """
    POST /api/twilio/recording
    Handle recording available webhook from Twilio.

    Twilio sends POST with:
    - RecordingSid: Unique recording identifier
    - RecordingUrl: URL to download recording
    - RecordingStatus: Status (completed, in-progress, absent)
    - RecordingDuration: Length in seconds
    - CallSid: Associated call SID
    - AccountSid: Twilio account SID

    This webhook:
    1. Downloads recording from Twilio
    2. Uploads to Supabase Storage
    3. Updates session with recording_sid and storage path
    4. Triggers transcription pipeline (Cloud Tasks or local)
    """

    def post(self, request):
        # Extract Twilio webhook parameters
        recording_sid = request.POST.get('RecordingSid')
        recording_url = request.POST.get('RecordingUrl')
        recording_status = request.POST.get('RecordingStatus')
        recording_duration = request.POST.get('RecordingDuration')
        call_sid = request.POST.get('CallSid')
        account_sid = request.POST.get('AccountSid')

        logger.info(
            f"[RECORDING-WEBHOOK] Received webhook - "
            f"CallSid={call_sid}, RecordingSid={recording_sid}, "
            f"Status={recording_status}, Duration={recording_duration}s"
        )

        # Validate required fields
        if not recording_sid or not call_sid:
            logger.error(
                f"[RECORDING-WEBHOOK] Missing required fields - "
                f"RecordingSid={recording_sid}, CallSid={call_sid}"
            )
            return Response(
                {'error': 'Missing RecordingSid or CallSid'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Only process completed recordings
        if recording_status != 'completed':
            logger.info(
                f"[RECORDING-WEBHOOK] Skipping non-completed recording - "
                f"RecordingSid={recording_sid}, Status={recording_status}"
            )
            return Response(
                {'message': f'Recording status: {recording_status}'},
                status=status.HTTP_200_OK
            )

        # Find session by call_sid
        supabase = get_supabase_client()
        if not supabase:
            logger.error("[RECORDING-WEBHOOK] Supabase client not available")
            return Response(
                {'error': 'Database not available'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            config = settings.APP_SETTINGS.supabase
            sessions_table = config.sessions_table

            # Find session by call_sid
            session_result = supabase.table(sessions_table).select('id').eq('call_sid', call_sid).execute()

            if not session_result.data or len(session_result.data) == 0:
                logger.error(
                    f"[RECORDING-WEBHOOK] Session not found - CallSid={call_sid}"
                )
                return Response(
                    {'error': f'Session not found for CallSid: {call_sid}'},
                    status=status.HTTP_404_NOT_FOUND
                )

            session_id = session_result.data[0]['id']

            logger.info(
                f"[RECORDING-WEBHOOK] Found session {session_id} for CallSid={call_sid}"
            )

            # Download recording from Twilio
            from apps.twilio.services import download_twilio_recording

            recording_data = download_twilio_recording(recording_sid, recording_url)

            if not recording_data['success']:
                logger.error(
                    f"[RECORDING-WEBHOOK] Failed to download recording - "
                    f"RecordingSid={recording_sid}, Error={recording_data['error']}"
                )
                return Response(
                    {'error': f"Failed to download recording: {recording_data['error']}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            logger.info(
                f"[RECORDING-WEBHOOK] Downloaded recording - "
                f"RecordingSid={recording_sid}, Size={len(recording_data['audio_bytes'])} bytes"
            )

            # Upload to Supabase Storage
            from apps.twilio.services import upload_recording_to_storage

            upload_result = upload_recording_to_storage(
                session_id=session_id,
                recording_sid=recording_sid,
                audio_bytes=recording_data['audio_bytes'],
                content_type=recording_data['content_type']
            )

            if not upload_result['success']:
                logger.error(
                    f"[RECORDING-WEBHOOK] Failed to upload recording - "
                    f"SessionId={session_id}, Error={upload_result['error']}"
                )
                return Response(
                    {'error': f"Failed to upload recording: {upload_result['error']}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            storage_path = upload_result['storage_path']

            logger.info(
                f"[RECORDING-WEBHOOK] Uploaded to storage - "
                f"SessionId={session_id}, Path={storage_path}"
            )

            # Update session with recording info
            from datetime import datetime

            update_data = {
                'recording_sid': recording_sid,
                'audio_storage_path': storage_path,
                'duration': int(recording_duration) if recording_duration else 0,
                'status': 'recorded',
                'recorded_at': datetime.utcnow().isoformat(),
                'last_event_received_at': datetime.utcnow().isoformat()
            }

            supabase.table(sessions_table).update(update_data).eq('id', session_id).execute()

            logger.info(
                f"[RECORDING-WEBHOOK] Updated session {session_id} - "
                f"RecordingSid={recording_sid}, StoragePath={storage_path}"
            )

            # Trigger transcription pipeline
            cloud_tasks_config = settings.APP_SETTINGS.cloud_tasks

            if cloud_tasks_config.enabled:
                # Production: Use Cloud Tasks
                from apps.core.services.cloud_tasks import enqueue_transcription_task
                import os

                service_url = os.getenv('CLOUD_RUN_SERVICE_URL')
                if not service_url:
                    k_service = os.getenv('K_SERVICE')
                    if k_service:
                        service_url = f'https://verc-app-staging-clw2hnetfa-uk.a.run.app'
                    else:
                        service_url = 'https://verc-app-staging-clw2hnetfa-uk.a.run.app'

                logger.info(f"[RECORDING-WEBHOOK] Enqueueing transcription task via Cloud Tasks")

                task_queued = enqueue_transcription_task(session_id, storage_path, service_url)

                if task_queued:
                    logger.info(
                        f"[RECORDING-WEBHOOK] ✅ Transcription task queued - SessionId={session_id}"
                    )
                else:
                    logger.warning(
                        f"[RECORDING-WEBHOOK] Failed to queue transcription task - SessionId={session_id}"
                    )
            else:
                # Local development: Use background processing
                from apps.core.services.background_tasks import process_transcription_locally

                logger.info(f"[RECORDING-WEBHOOK] Triggering local transcription")
                process_transcription_locally(session_id, storage_path)

            # Return success
            return Response({
                'success': True,
                'message': 'Recording processed successfully',
                'sessionId': session_id,
                'recordingSid': recording_sid,
                'storagePath': storage_path
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(
                f"[RECORDING-WEBHOOK] Error processing recording - "
                f"RecordingSid={recording_sid}, Error={str(e)}",
                exc_info=True
            )
            return Response(
                {'error': f'Failed to process recording: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TranscriptsView(APIView):
    """
    POST /api/twilio/transcripts
    Handle real-time transcript webhook.
    """
    def post(self, request):
        # TODO: Implement transcript webhook
        return Response({'message': 'Transcript webhook - to be implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED)


class TranscriptionStatusView(APIView):
    """
    POST /api/twilio/transcription-status
    Handle transcription status webhook.
    """
    def post(self, request):
        # TODO: Implement transcription status webhook
        return Response({'message': 'Transcription status webhook - to be implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED)


class MakeCallView(APIView):
    """
    POST /api/twilio/make-call
    Initiate outbound call.
    """
    def post(self, request):
        # TODO: Implement make call
        return Response({'message': 'Make call - to be implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED)


class HangupView(APIView):
    """
    POST /api/twilio/hangup/<call_sid>
    Hangup active call.
    """
    def post(self, request, call_sid):
        # TODO: Implement hangup
        return Response({'message': 'Hangup - to be implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED)


class StatusView(APIView):
    """
    GET /api/twilio/status
    Twilio service health check.
    """
    def get(self, request):
        return Response({'status': 'ok', 'service': 'twilio'}, status=status.HTTP_200_OK)

