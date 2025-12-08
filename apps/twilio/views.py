"""
Twilio webhook views.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class VoiceWebhookView(APIView):
    """
    POST /api/twilio/voice
    Handle incoming call - returns TwiML.
    """
    def post(self, request):
        # TODO: Implement Twilio voice webhook
        return Response({'message': 'Voice webhook - to be implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED)


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

