"""
Twilio webhook views.
"""
from django.http import HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from twilio.twiml.voice_response import VoiceResponse
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


class RecordingView(APIView):
    """
    POST /api/twilio/recording
    Handle recording available webhook.
    """
    def post(self, request):
        # TODO: Implement recording webhook
        return Response({'message': 'Recording webhook - to be implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED)


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

