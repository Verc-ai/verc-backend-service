"""
Session management routes.
Frontend expects:
- GET /api/sessions/{id}
- POST /api/sessions/{id}/generate-summary
- POST /api/sessions/{id}/generate-scorecard
"""
from django.urls import path
from . import views

app_name = 'call_sessions'

urlpatterns = [
    path('', views.SessionListView.as_view(), name='list'),  # GET /api/sessions/
    path('<str:session_id>', views.SessionDetailView.as_view(), name='detail'),  # GET /api/sessions/{id}
    path('<str:session_id>/generate-summary', views.GenerateSummaryView.as_view(), name='generate-summary'),  # POST /api/sessions/{id}/generate-summary
    path('<str:session_id>/generate-scorecard', views.GenerateScorecardView.as_view(), name='generate-scorecard'),  # POST /api/sessions/{id}/generate-scorecard
]

