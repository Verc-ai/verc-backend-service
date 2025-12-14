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
    path('start-spy-call/', views.StartSpyCallView.as_view(), name='start-spy-call'),
    path('start-spy-call', views.StartSpyCallView.as_view(), name='start-spy-call-no-slash'),  # Without trailing slash
    path('cleanup-spy-call/', views.CleanupSpyCallView.as_view(), name='cleanup-spy-call'),
    path('cleanup-spy-call', views.CleanupSpyCallView.as_view(), name='cleanup-spy-call-no-slash'),  # Without trailing slash
]

