"""
Feature flags routes.
Frontend expects:
- GET /api/feature-flags
- POST /api/feature-flags
- PATCH /api/feature-flags/{id}
"""
from django.urls import path
from . import views

app_name = 'feature_flags'

urlpatterns = [
    path('', views.FeatureFlagListView.as_view(), name='list'),  # GET, POST /api/feature-flags
    path('<str:flag_id>', views.FeatureFlagDetailView.as_view(), name='detail'),  # PATCH /api/feature-flags/{id}
]

