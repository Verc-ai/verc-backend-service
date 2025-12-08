"""
Cloud Tasks handler routes.
"""
from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    path('transcribe-audio/', views.TranscribeAudioView.as_view(), name='transcribe-audio'),
    path('transcribe-audio', views.TranscribeAudioView.as_view(), name='transcribe-audio-no-slash'),  # Without trailing slash
    path('generate-ai-analysis/', views.GenerateAIAnalysisView.as_view(), name='generate-ai-analysis'),
    path('generate-ai-analysis', views.GenerateAIAnalysisView.as_view(), name='generate-ai-analysis-no-slash'),  # Without trailing slash
]

