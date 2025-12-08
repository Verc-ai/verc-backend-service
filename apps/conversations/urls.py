"""
Conversation routes.
Frontend expects:
- POST /api/conversation/upload
- POST /api/conversation/simulate
- GET /api/conversation/audio/signed-url
"""
from django.urls import path
from . import views

app_name = 'conversations'

urlpatterns = [
    path('upload', views.UploadView.as_view(), name='upload'),  # Frontend expects /api/conversation/upload
    path('simulate', views.SimulateView.as_view(), name='simulate'),  # Frontend expects /api/conversation/simulate
    path('audio/signed-url', views.SignedUrlView.as_view(), name='signed-url'),  # Frontend expects /api/conversation/audio/signed-url
]

