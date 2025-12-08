"""
Call sessions views for managing transcription sessions.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from apps.core.services.supabase import get_supabase_client
from django.conf import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def calculate_session_duration(created_at: str, last_event_at: str) -> int:
    """
    Calculate session duration in seconds.
    
    Args:
        created_at: Session creation timestamp
        last_event_at: Last event received timestamp
        
    Returns:
        int: Duration in seconds, or None if calculation fails
    """
    if not created_at or not last_event_at:
        return None
    
    try:
        last_event = datetime.fromisoformat(last_event_at.replace('Z', '+00:00'))
        created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        return int((last_event - created).total_seconds())
    except Exception as e:
        logger.warning(f'Failed to calculate duration: {e}')
        return None


class SessionListView(APIView):
    permission_classes = [AllowAny]  # Allow access with mock tokens
    """
    GET /api/sessions/
    List all call sessions.
    Frontend expects: { sessions: [...], total: number }
    """
    def get(self, request):
        supabase = get_supabase_client()
        
        if not supabase:
            logger.warning('Supabase client not available, returning empty list')
            # Log configuration status for debugging
            from django.conf import settings
            config = settings.APP_SETTINGS.supabase
            logger.warning(f'Supabase config - URL: {bool(config.url)}, Service Key: {bool(config.service_role_key)}')
            logger.warning(f'Supabase config details - URL length: {len(config.url) if config.url else 0}, Key length: {len(config.service_role_key) if config.service_role_key else 0}, URL empty: {not config.url or config.url.strip() == ""}, Key empty: {not config.service_role_key or config.service_role_key.strip() == ""}')
            return Response({
                'sessions': [],
                'total': 0,
                'debug': 'Supabase client not available'
            }, status=status.HTTP_200_OK)
        
        logger.info('Fetching sessions from Supabase...')
        try:
            # Get query parameters
            limit = int(request.query_params.get('limit', 50))
            offset = int(request.query_params.get('offset', 0))
            sort_by = request.query_params.get('sortBy', 'created_at')
            sort_order = request.query_params.get('sortOrder', 'desc')
            
            # Build query
            query = supabase.table('transcription_sessions').select('*', count='exact')
            
            # Apply filters
            status_filter = request.query_params.get('status')
            if status_filter:
                # Status might be in metadata, try both JSON path and direct column
                # Note: Supabase PostgREST doesn't support complex JSON queries easily
                # We'll filter after fetching if needed, or use a simpler approach
                pass  # TODO: Implement status filtering via metadata
            
            date_from = request.query_params.get('dateFrom')
            if date_from:
                query = query.gte('created_at', date_from)
            
            date_to = request.query_params.get('dateTo')
            if date_to:
                query = query.lte('created_at', date_to)
            
            phone_number = request.query_params.get('phoneNumber')
            if phone_number:
                # Search in caller_number (we'll filter dialed_number in Python if needed)
                query = query.ilike('caller_number', f'%{phone_number}%')
            
            # Apply sorting
            if sort_order == 'desc':
                query = query.order(sort_by, desc=True)
            else:
                query = query.order(sort_by, desc=False)
            
            # Apply pagination
            query = query.range(offset, offset + limit - 1)
            
            # Execute query
            response = query.execute()
            
            logger.info(f'Fetched {len(response.data)} sessions from Supabase')
            if len(response.data) == 0:
                logger.info('No sessions found in database. Checking if table exists and has data...')
            
            # Get turn counts for all sessions (fetch all events and count in Python)
            session_ids = [row.get('id') for row in response.data if row.get('id')]
            logger.info(f'Processing {len(session_ids)} sessions')
            turn_counts = {sid: 0 for sid in session_ids}  # Initialize all to 0
            if session_ids:
                try:
                    # Fetch all events for these sessions in batches if needed
                    # Supabase has a limit, so we might need to paginate
                    events_response = supabase.table('transcription_events')\
                        .select('session_id')\
                        .in_('session_id', session_ids)\
                        .execute()
                    
                    # Count events per session
                    for event in events_response.data:
                        session_id = event.get('session_id')
                        if session_id and session_id in turn_counts:
                            turn_counts[session_id] = turn_counts.get(session_id, 0) + 1
                except Exception as e:
                    logger.warning(f'Failed to fetch turn counts: {e}')
            
            # Transform sessions to match frontend format
            sessions = []
            for row in response.data:
                # Apply status filter if specified (post-filter since it's in metadata)
                status_filter = request.query_params.get('status')
                if status_filter:
                    session_status_check = 'created'
                    if row.get('metadata') and isinstance(row.get('metadata'), dict):
                        session_status_check = row['metadata'].get('status', 'created')
                    elif row.get('last_event_received_at'):
                        session_status_check = 'transcribed'
                    
                    if session_status_check != status_filter:
                        continue  # Skip this session
                
                # Apply duration filters if specified
                min_duration = request.query_params.get('minDuration')
                max_duration = request.query_params.get('maxDuration')
                
                # Calculate duration using helper function
                duration = calculate_session_duration(
                    row.get('created_at'),
                    row.get('last_event_received_at')
                )
                
                # Apply duration filters
                if min_duration and (duration is None or duration < int(min_duration)):
                    continue
                if max_duration and duration and duration > int(max_duration):
                    continue
                
                # Apply phone number filter for dialed_number (if caller_number didn't match)
                phone_number = request.query_params.get('phoneNumber')
                if phone_number:
                    caller_match = row.get('caller_number', '').lower().find(phone_number.lower()) >= 0
                    dialed_match = row.get('dialed_number', '').lower().find(phone_number.lower()) >= 0
                    if not caller_match and not dialed_match:
                        continue  # Skip if neither matches
                session_id = row.get('id')
                # Get turn count from events query or metadata
                turn_count = turn_counts.get(session_id, 0)
                if turn_count == 0 and row.get('metadata') and isinstance(row.get('metadata'), dict):
                    turn_count = row['metadata'].get('turn_count', 0)
                
                # Calculate duration if not already calculated above
                if duration is None:
                    duration = calculate_session_duration(
                        row.get('created_at'),
                        row.get('last_event_received_at')
                    )
                
                # Derive status from metadata or use default
                session_status = 'created'
                if row.get('metadata') and isinstance(row.get('metadata'), dict):
                    session_status = row['metadata'].get('status', 'created')
                elif row.get('last_event_received_at'):
                    session_status = 'transcribed'
                
                # Get caller number
                caller_number = row.get('caller_number')
                if not caller_number and row.get('metadata') and isinstance(row.get('metadata'), dict):
                    caller_number = row['metadata'].get('caller_number') or row['metadata'].get('from')
                
                # Get overall score from scorecard data
                overall_score = None
                if row.get('call_scorecard_data') and isinstance(row.get('call_scorecard_data'), dict):
                    overall_score = row['call_scorecard_data'].get('overall_weighted_score')
                
                session = {
                    'id': row.get('id'),
                    'created_at': row.get('created_at'),
                    'last_event_received_at': row.get('last_event_received_at'),
                    'duration': duration,
                    'caller_number': caller_number,
                    'call_status': session_status,  # Legacy field
                    'status': session_status,
                    'turn_count': turn_count,
                    'metadata': row.get('metadata'),
                    'call_summary_status': row.get('call_summary_status', 'not_started'),
                    'call_scorecard_status': row.get('call_scorecard_status', 'not_started'),
                    'overall_weighted_score': overall_score,
                }
                sessions.append(session)
            
            return Response({
                'sessions': sessions,
                'total': response.count if hasattr(response, 'count') else len(sessions),
                'limit': limit,
                'offset': offset,
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f'Error fetching sessions: {e}', exc_info=True)
            import traceback
            logger.error(f'Traceback: {traceback.format_exc()}')
            return Response({
                'sessions': [],
                'total': 0,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SessionDetailView(APIView):
    permission_classes = [AllowAny]  # Allow access with mock tokens
    
    """
    GET /api/sessions/{id}
    Get call session details.
    Frontend expects: session object with all call details
    """
    def get(self, request, session_id):
        # TODO: Implement session detail retrieval from Supabase
        # For now, return a mock response
        return Response({
            'id': session_id,
            'status': 'transcribed',
            'transcription': [],
            'summary': None,
            'scorecard': None,
            'metadata': {}
        }, status=status.HTTP_200_OK)


class GenerateSummaryView(APIView):
    """
    POST /api/sessions/{id}/generate-summary
    Generate AI summary for a call session.
    """
    def post(self, request, session_id):
        # TODO: Implement AI summary generation
        return Response({
            'message': 'Summary generation started (mock)',
            'sessionId': session_id
        }, status=status.HTTP_200_OK)


class GenerateScorecardView(APIView):
    """
    POST /api/sessions/{id}/generate-scorecard
    Generate AI scorecard for a call session.
    """
    def post(self, request, session_id):
        # TODO: Implement AI scorecard generation
        return Response({
            'message': 'Scorecard generation started (mock)',
            'sessionId': session_id
        }, status=status.HTTP_200_OK)

