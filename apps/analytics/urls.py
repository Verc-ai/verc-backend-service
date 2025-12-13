"""
Analytics routes.
Frontend expects:
- GET /api/analytics/scorecard/
- GET /api/analytics/trends/
- GET /api/analytics/health/
"""
from django.urls import path
from .views import scorecard, trends, health

app_name = 'analytics'

urlpatterns = [
    path('scorecard/', scorecard.ScorecardView.as_view(), name='scorecard'),
    path('trends/', trends.TrendsView.as_view(), name='trends'),
    path('health/', health.HealthView.as_view(), name='health'),
]

