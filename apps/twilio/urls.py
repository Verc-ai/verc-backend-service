"""
Twilio webhook routes.
"""
from django.urls import path
from . import views

app_name = 'twilio'

urlpatterns = [
    path('voice/', views.VoiceWebhookView.as_view(), name='voice'),
    path('call-status/', views.CallStatusView.as_view(), name='call-status'),
    path('recording/', views.RecordingView.as_view(), name='recording'),
    path('transcripts/', views.TranscriptsView.as_view(), name='transcripts'),
    path('transcription-status/', views.TranscriptionStatusView.as_view(), name='transcription-status'),
    path('make-call/', views.MakeCallView.as_view(), name='make-call'),
    path('hangup/<str:call_sid>/', views.HangupView.as_view(), name='hangup'),
    path('status/', views.StatusView.as_view(), name='status'),
]

