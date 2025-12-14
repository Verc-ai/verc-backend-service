"""
Feature flags views for managing application feature flags.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from apps.core.services.supabase import get_supabase_client
import logging

logger = logging.getLogger(__name__)


def get_default_feature_flags():
    """
    Get default feature flags to enable basic functionality.

    Returns:
        list: List of default feature flag dictionaries
    """
    return [
        {
            'id': 'default-audio-transcription',
            'key': 'audio-file-transcription',
            'name': 'Audio File Transcription',
            'description': 'Enable audio file upload and transcription',
            'enabled': True,
            'metadata': None,
        },
        {
            'id': 'default-call-history',
            'key': 'call-history',
            'name': 'Call History',
            'description': 'Enable call history page',
            'enabled': True,
            'metadata': None,
        },
        {
            'id': 'default-pbx-monitor',
            'key': 'pbx-monitor',
            'name': 'Buffalo PBX Monitor',
            'description': 'Enable Buffalo PBX WebSocket monitor for automated SPY call recording',
            'enabled': True,
            'metadata': None,
        },
    ]


class FeatureFlagListView(APIView):
    permission_classes = [AllowAny]  # Allow access with mock tokens
    """
    GET /api/feature-flags - List all feature flags
    POST /api/feature-flags - Create a new feature flag
    Frontend expects: { featureFlags: [...] } for GET, { featureFlag: {...} } for POST
    """
    parser_classes = [JSONParser]
    
    def get(self, request):
        supabase = get_supabase_client()
        
        if supabase:
            try:
                # Fetch feature flags from Supabase
                from django.conf import settings
                config = settings.APP_SETTINGS.supabase
                table_name = config.feature_flags_table
                
                response = supabase.table(table_name).select('*').execute()
                
                # Transform to match frontend format
                flags = []
                for row in response.data:
                    flags.append({
                        'id': row.get('id'),
                        'key': row.get('flag_key'),  # Supabase uses flag_key, frontend expects key
                        'name': row.get('name'),
                        'description': row.get('description'),
                        'enabled': row.get('enabled', False),
                        'metadata': row.get('metadata'),
                        'createdAt': row.get('created_at'),
                        'updatedAt': row.get('updated_at'),
                    })
                
                logger.info(f'Fetched {len(flags)} feature flags from Supabase')
                
                # If no flags found, return default flags to enable basic features
                if len(flags) == 0:
                    logger.info('No feature flags found, returning default flags')
                    flags = get_default_feature_flags()
                
                return Response({
                    'featureFlags': flags
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f'Error fetching feature flags: {e}', exc_info=True)
                # Fall through to default flags
        
        # Fallback: return default flags if Supabase is not available
        logger.warning('Supabase not available, returning default feature flags')
        return Response({
            'featureFlags': get_default_feature_flags()
        }, status=status.HTTP_200_OK)
    
    def post(self, request):
        # TODO: Create feature flag in Supabase
        # For now, return mock response
        import uuid
        flag_data = request.data
        return Response({
            'featureFlag': {
                'id': str(uuid.uuid4()),
                'key': flag_data.get('key', ''),
                'name': flag_data.get('name', ''),
                'description': flag_data.get('description', ''),
                'enabled': flag_data.get('enabled', True),
            }
        }, status=status.HTTP_201_CREATED)


class FeatureFlagDetailView(APIView):
    permission_classes = [AllowAny]  # Allow access with mock tokens
    
    """
    PATCH /api/feature-flags/{id} - Update a feature flag
    Frontend expects: { featureFlag: {...} }
    """
    parser_classes = [JSONParser]
    
    def patch(self, request, flag_id):
        # TODO: Update feature flag in Supabase
        # For now, return mock response
        return Response({
            'featureFlag': {
                'id': flag_id,
                'enabled': request.data.get('enabled', True),
            }
        }, status=status.HTTP_200_OK)

