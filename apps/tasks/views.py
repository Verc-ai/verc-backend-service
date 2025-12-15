"""
Cloud Tasks handler views for async transcription and AI analysis.
"""
import sys
import os
import logging
from datetime import datetime, timedelta, timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.core.services.supabase import get_supabase_client
from apps.core.utils import format_timestamp

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class TranscribeAudioView(APIView):
    """
    POST /api/tasks/transcribe-audio
    Process uploaded audio file: transcribe and save to database.
    
    Body: { sessionId, storagePath }
    
    Note: This endpoint is called by Google Cloud Tasks.
    Cloud Tasks will include OIDC token authentication and task headers.
    """
    permission_classes = [AllowAny]  # Cloud Tasks authenticates via OIDC token
    parser_classes = [JSONParser]
    
    def post(self, request):
        # Log Cloud Tasks headers for debugging
        task_name = request.headers.get('X-CloudTasks-TaskName', 'N/A')
        queue_name = request.headers.get('X-CloudTasks-QueueName', 'N/A')
        print(f'[TASK] 🔵 Cloud Tasks request received: taskName={task_name}, queueName={queue_name}', file=sys.stderr, flush=True)
        logger.info(
            f'🔵 Cloud Tasks request received: taskName={task_name}, queueName={queue_name}, '
            f'path={request.path}, method={request.method}'
        )
        
        session_id = request.data.get('sessionId')
        storage_path = request.data.get('storagePath')
        
        print(f'[TASK] Request data: sessionId={session_id}, storagePath={storage_path}', file=sys.stderr, flush=True)
        
        if not session_id or not storage_path:
            print(f'[TASK] ❌ Missing required fields: sessionId={session_id}, storagePath={storage_path}', file=sys.stderr, flush=True)
            logger.error(f'Missing required fields: sessionId={session_id}, storagePath={storage_path}')
            return Response(
                {'error': 'Missing sessionId or storagePath'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        print(f'[TASK] Received transcription task: sessionId={session_id}, storagePath={storage_path}', file=sys.stderr, flush=True)
        logger.info(f'Received transcription task: sessionId={session_id}, storagePath={storage_path}')
        
        # Update session status to indicate transcription is starting
        supabase = get_supabase_client()
        if supabase:
            try:
                config = settings.APP_SETTINGS.supabase
                table_name = config.sessions_table
                
                print(f'[TASK] Updating session {session_id} status to transcribing in table {table_name}', file=sys.stderr, flush=True)
                
                # Update session status
                now = format_timestamp()
                result = supabase.table(table_name).update({
                    'status': 'transcribing',
                    'transcription_started_at': now,
                    'last_event_received_at': now
                }).eq('id', session_id).execute()
                
                print(f'[TASK] ✅ Updated session {session_id} status to transcribing. Result: {result}', file=sys.stderr, flush=True)
                logger.info(f'Updated session {session_id} status to transcribing')
            except Exception as e:
                print(f'[TASK] ❌ Failed to update session status: {e}', file=sys.stderr, flush=True)
                import traceback
                print(f'[TASK] Traceback: {traceback.format_exc()}', file=sys.stderr, flush=True)
                logger.error(f'Failed to update session status: {e}', exc_info=True)
        else:
            print(f'[TASK] ❌ Supabase client not available', file=sys.stderr, flush=True)
        
        # Implement real transcription logic:
        # 1. Get signed URL from Supabase Storage using storage_path
        # 2. Transcribe using AssemblyAI
        # 3. Save transcription events to Supabase
        # 4. Update session status to 'transcribed' when done
        # 5. Queue AI analysis task when transcription completes
        
        if not supabase:
            logger.error('Supabase client not available for transcription')
            return Response(
                {'error': 'Supabase client not available'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        try:
            from apps.core.services.cloud_tasks import enqueue_ai_analysis_task
            from apps.ai.transcription_service import get_transcription_service
            import uuid
            
            config = settings.APP_SETTINGS.supabase
            table_name = config.sessions_table
            events_table = config.events_table
            bucket = config.audio_bucket
            
            print(f'[TASK] Starting real transcription for session {session_id}, storage_path={storage_path}', file=sys.stderr, flush=True)
            logger.info(f'Starting real transcription for session {session_id}')
            
            # Step 1: Get signed URL from Supabase Storage
            print(f'[TASK] Generating signed URL for storage path: {storage_path}', file=sys.stderr, flush=True)
            signed_url = None
            try:
                signed_url_response = supabase.storage.from_(bucket).create_signed_url(
                    storage_path,
                    expires_in=3600  # 1 hour
                )
                
                # Log the response type for debugging
                print(f'[TASK] Signed URL response type: {type(signed_url_response)}', file=sys.stderr, flush=True)
                logger.debug(f'Signed URL response type: {type(signed_url_response)}, response: {signed_url_response}')
                
                # Handle different response formats from Supabase Python client
                if isinstance(signed_url_response, dict):
                    # Response is a dict with 'signedURL' or 'error' key
                    if 'error' in signed_url_response:
                        error_msg = signed_url_response.get('error', 'Unknown error')
                        raise Exception(f'Failed to generate signed URL: {error_msg}')
                    elif 'signedURL' in signed_url_response:
                        signed_url = signed_url_response['signedURL']
                    elif 'data' in signed_url_response:
                        data = signed_url_response['data']
                        if isinstance(data, dict):
                            signed_url = data.get('signedURL')
                        elif hasattr(data, 'signedURL'):
                            signed_url = data.signedURL
                elif hasattr(signed_url_response, 'error') and signed_url_response.error:
                    raise Exception(f'Failed to generate signed URL: {signed_url_response.error}')
                elif hasattr(signed_url_response, 'signedURL'):
                    signed_url = signed_url_response.signedURL
                elif hasattr(signed_url_response, 'data'):
                    data = signed_url_response.data
                    if isinstance(data, dict):
                        signed_url = data.get('signedURL')
                    elif hasattr(data, 'signedURL'):
                        signed_url = data.signedURL
                elif isinstance(signed_url_response, str):
                    # Sometimes the response is just the URL string
                    signed_url = signed_url_response
                
                if signed_url:
                    logger.info(f'Generated signed URL for {storage_path}')
                    print(f'[TASK] ✅ Generated signed URL: {signed_url[:100]}...', file=sys.stderr, flush=True)
                else:
                    raise Exception(f'Failed to generate signed URL - response format unexpected. Response type: {type(signed_url_response)}, Response: {str(signed_url_response)[:200]}')
            except Exception as e:
                logger.error(f'Failed to generate signed URL: {e}', exc_info=True)
                print(f'[TASK] ❌ Failed to generate signed URL: {e}', file=sys.stderr, flush=True)
                raise
            
            # Step 2: Transcribe using AssemblyAI
            print(f'[TASK] Starting AssemblyAI transcription...', file=sys.stderr, flush=True)
            logger.info(f'Transcription service check: ASSEMBLYAI_API_KEY configured = {bool(settings.APP_SETTINGS.ai.assemblyai_api_key)}')
            
            transcription_service = get_transcription_service()
            if not transcription_service:
                error_msg = 'Transcription service not available - check ASSEMBLYAI_API_KEY configuration'
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # Speaker mapping: A = agent, B = customer (default)
            speaker_mapping = {'A': 'agent', 'B': 'customer'}
            
            print(f'[TASK] Calling AssemblyAI transcription service with signed URL...', file=sys.stderr, flush=True)
            logger.info(f'Calling AssemblyAI transcription for session {session_id}')
            
            try:
                turns = transcription_service.transcribe_with_diarization(
                    audio_url=signed_url,
                    speaker_mapping=speaker_mapping
                )
            except Exception as transcribe_error:
                error_msg = f'AssemblyAI transcription failed: {str(transcribe_error)}'
                logger.error(error_msg, exc_info=True)
                print(f'[TASK] ❌ {error_msg}', file=sys.stderr, flush=True)
                raise Exception(error_msg)
            
            if not turns:
                raise Exception('No transcription turns returned from AssemblyAI - transcription may have failed silently')
            
            print(f'[TASK] ✅ Transcription completed: {len(turns)} turns', file=sys.stderr, flush=True)
            logger.info(f'Transcription completed: {len(turns)} turns for session {session_id}')
            
            # Step 3: Fetch session metadata to include in event payloads (matches old backend structure)
            print(f'[TASK] Fetching session metadata for event payloads...', file=sys.stderr, flush=True)
            session_metadata_payload = {
                'source': 'audio-upload',  # Default source
                'storagePath': storage_path,  # Use storage_path from request
                'uploadedAt': None,
                'originalName': None
            }
            
            try:
                session_response = supabase.table(table_name).select('metadata, audio_storage_path, created_at').eq('id', session_id).execute()
                if session_response.data and len(session_response.data) > 0:
                    session_data = session_response.data[0]
                    session_metadata = session_data.get('metadata', {})
                    
                    # Extract session metadata fields (same structure as old backend)
                    if isinstance(session_metadata, dict):
                        session_metadata_payload['source'] = session_metadata.get('source', 'audio-upload')
                        session_metadata_payload['storagePath'] = session_metadata.get('storagePath') or session_data.get('audio_storage_path') or storage_path
                        session_metadata_payload['originalName'] = session_metadata.get('originalName')
                        session_metadata_payload['uploadedAt'] = session_metadata.get('uploadedAt') or session_data.get('created_at')
                    
                    logger.debug(f'Fetched session metadata for {session_id}: {session_metadata_payload}')
            except Exception as e:
                logger.warning(f'Failed to fetch session metadata: {e} - using defaults')
            
            # Step 4: Convert turns to Supabase event format and insert
            print(f'[TASK] Converting {len(turns)} turns to Supabase event format...', file=sys.stderr, flush=True)
            now = datetime.now(timezone.utc)
            finalized_at = format_timestamp(now)
            ended_at = format_timestamp(now)
            
            # Build full transcript text (all turns combined)
            full_transcript_lines = []
            for turn in turns:
                speaker = turn.get('speaker', 'unknown')
                text = turn.get('text', '')
                if text:
                    full_transcript_lines.append(f"{speaker}: {text}")
            full_transcript = '\n'.join(full_transcript_lines)
            
            events = []
            
            for idx, turn in enumerate(turns):
                # Generate unique turnId for each turn
                turn_id = str(uuid.uuid4())
                
                # Calculate timestamp based on start_time_ms or use sequential timing
                if turn.get('start_time_ms'):
                    # Use actual timestamp from audio
                    event_time = now + timedelta(milliseconds=turn['start_time_ms'])
                else:
                    # Fallback to sequential timing
                    event_time = now + timedelta(seconds=idx * 5)
                
                # Build payload matching old backend structure exactly:
                # Old backend includes: source, turnId, startTime, endTime, duration, sentiment, confidence,
                # totalTurns, finalizedAt, endedAt, simulationId, fullTranscript, storagePath, originalName, uploadedAt
                turn_metadata = turn.get('metadata', {})  # Contains speaker_label, transcript_id, etc.
                
                # Get timing values (convert from _ms to camelCase to match old backend)
                start_time = turn.get('start_time_ms')
                end_time = turn.get('end_time_ms')
                duration = turn.get('duration_ms')
                
                event_payload = {
                    # Session metadata (from session record)
                    'source': 'audio-file',  # Old backend uses 'audio-file', not 'audio-upload'
                    'storagePath': session_metadata_payload['storagePath'],
                    'originalName': session_metadata_payload.get('originalName'),
                    'uploadedAt': session_metadata_payload.get('uploadedAt'),
                    # Transcription turn metadata (matching old backend field names)
                    'turnId': turn_id,
                    'startTime': start_time,  # Old backend uses startTime (not start_time_ms)
                    'endTime': end_time,  # Old backend uses endTime (not end_time_ms)
                    'duration': duration,  # Old backend uses duration (not duration_ms)
                    'sentiment': turn.get('sentiment'),
                    'confidence': turn.get('confidence'),
                    # Session-level metadata (same for all turns)
                    'simulationId': session_id,  # session_id is the simulationId
                    'totalTurns': len(turns),
                    'fullTranscript': full_transcript,
                    'finalizedAt': finalized_at,
                    'endedAt': ended_at,
                    # PII and other fields
                    'pii_entities_detected': turn.get('pii_entities_detected'),
                }
                
                # Add turn-specific metadata (speaker_label, transcript_id, etc.) directly to payload
                # This matches the old backend structure where all metadata is flat
                if turn_metadata:
                    event_payload.update(turn_metadata)
                
                # Remove None values to keep payload clean
                event_payload = {k: v for k, v in event_payload.items() if v is not None}
                
                # Debug: Log first event payload structure for verification
                if idx == 0:
                    print(f'[TASK] 📋 First event payload keys: {list(event_payload.keys())}', file=sys.stderr, flush=True)
                    print(f'[TASK] 📋 First event payload sample: {str(event_payload)[:500]}', file=sys.stderr, flush=True)
                
                event = {
                    'id': str(uuid.uuid4()),
                    'session_id': session_id,
                    'speaker': turn.get('speaker', 'unknown'),
                    'text': turn.get('text', ''),
                    'received_at': format_timestamp(event_time),
                    'payload': event_payload,
                    'pii_redacted': turn.get('pii_redacted', False)
                }
                
                events.append(event)
            
            # Step 5: Batch insert events
            print(f'[TASK] Inserting {len(events)} transcription events into {events_table}...', file=sys.stderr, flush=True)
            # Debug: Show what's being inserted
            if events:
                first_event_payload_keys = list(events[0].get('payload', {}).keys())
                print(f'[TASK] 📋 First event payload contains {len(first_event_payload_keys)} keys: {first_event_payload_keys}', file=sys.stderr, flush=True)
            try:
                result = supabase.table(events_table).insert(events).execute()
                print(f'[TASK] ✅ Successfully inserted {len(events)} transcription events', file=sys.stderr, flush=True)
                logger.info(f'Created {len(events)} transcription events for session {session_id}')
            except Exception as e:
                print(f'[TASK] ❌ Failed to insert transcription events: {e}', file=sys.stderr, flush=True)
                import traceback
                print(f'[TASK] Traceback: {traceback.format_exc()}', file=sys.stderr, flush=True)
                logger.error(f'Failed to insert transcription events: {e}', exc_info=True)
                raise
            
            # Step 6: Update session status to transcribed and finalize metadata
            print(f'[TASK] Updating session {session_id} status to transcribed...', file=sys.stderr, flush=True)
            now = format_timestamp()
            
            # Fetch existing session metadata to preserve it
            try:
                existing_session = supabase.table(table_name).select('metadata').eq('id', session_id).execute()
                existing_metadata = {}
                if existing_session.data and len(existing_session.data) > 0:
                    existing_metadata = existing_session.data[0].get('metadata', {}) or {}
            except Exception as e:
                logger.warning(f'Failed to fetch existing session metadata: {e} - will use defaults')
                existing_metadata = {}
            
            # Get last turn data for session metadata (matching old backend structure)
            # The session metadata includes the last turn's metadata plus session summary
            last_turn = turns[-1] if turns else None
            last_turn_id = None
            last_start_time = None
            last_end_time = None
            last_duration = None
            last_sentiment = None
            last_confidence = None
            
            if last_turn:
                # Get data from the last event we created (has all the processed fields)
                if events:
                    last_event_payload = events[-1].get('payload', {})
                    last_turn_id = last_event_payload.get('turnId')
                    last_start_time = last_event_payload.get('startTime')
                    last_end_time = last_event_payload.get('endTime')
                    last_duration = last_event_payload.get('duration')
                    last_sentiment = last_event_payload.get('sentiment')
                    last_confidence = last_event_payload.get('confidence')
                
                # Fallback to turn data if not in payload yet
                if not last_turn_id:
                    last_start_time = last_turn.get('start_time_ms')
                    last_end_time = last_turn.get('end_time_ms')
                    last_duration = last_turn.get('duration_ms')
                    last_sentiment = last_turn.get('sentiment')
                    last_confidence = last_turn.get('confidence')
            
            # Calculate duration in seconds from last turn's endTime (if available)
            duration_seconds = None
            if last_end_time:
                duration_seconds = int(last_end_time / 1000)  # Convert ms to seconds
            elif last_duration:
                duration_seconds = int(last_duration / 1000)  # duration is already in ms
            
            # Update session metadata with transcription summary (matching old backend structure exactly)
            # Exact order: source, turnId, endTime, endedAt, duration, sentiment, startTime, confidence, totalTurns, finalizedAt, simulationId, fullTranscript
            # Also preserve existing fields: storagePath, originalName, uploadedAt (will be added after core fields)
            
            # Build metadata in exact order specified
            updated_metadata = {
                'source': 'audio-file',  # Old backend uses 'audio-file', not 'audio-upload'
                'turnId': last_turn_id,
                'endTime': last_end_time,
                'endedAt': ended_at,
                'duration': duration_seconds if duration_seconds is not None else last_duration,
                'sentiment': last_sentiment,
                'startTime': last_start_time,
                'confidence': last_confidence,
                'totalTurns': len(turns),
                'finalizedAt': finalized_at,
                'simulationId': session_id,
                'fullTranscript': full_transcript,
            }
            
            # Preserve existing session metadata fields (storagePath, originalName, uploadedAt) that aren't in core fields
            preserved_fields = {k: v for k, v in existing_metadata.items() 
                              if k not in ['source', 'turnId', 'endTime', 'endedAt', 'duration', 'sentiment', 
                                         'startTime', 'confidence', 'totalTurns', 'finalizedAt', 'simulationId', 'fullTranscript']}
            updated_metadata.update(preserved_fields)
            
            # Remove None values but keep 0, False, and empty strings
            updated_metadata = {k: v for k, v in updated_metadata.items() if v is not None}
            
            result = supabase.table(table_name).update({
                'status': 'transcribed',
                'transcription_completed_at': now,
                'last_event_received_at': now,
                'metadata': updated_metadata
            }).eq('id', session_id).execute()
            
            print(f'[TASK] ✅ Updated session {session_id} status to transcribed with metadata summary', file=sys.stderr, flush=True)
            logger.info(f'Updated session {session_id} status to transcribed with {len(turns)} turns')
            
            # Step 7: Queue AI analysis task (Cloud Tasks or local processing)
            cloud_tasks_config = settings.APP_SETTINGS.cloud_tasks

            if cloud_tasks_config.enabled:
                # Production/Staging: Use Cloud Tasks
                service_url = os.getenv('CLOUD_RUN_SERVICE_URL')
                if not service_url:
                    k_service = os.getenv('K_SERVICE')
                    if k_service:
                        service_url = f'https://verc-app-staging-clw2hnetfa-uk.a.run.app'
                    else:
                        service_url = 'https://verc-app-staging-clw2hnetfa-uk.a.run.app'

                logger.info(f'Using service URL for AI analysis task: {service_url}')

                ai_task_queued = enqueue_ai_analysis_task(session_id, service_url)
                if ai_task_queued:
                    logger.info(f'✅ AI analysis task queued for session {session_id}')
                    print(f'[TASK] ✅ AI analysis task queued', file=sys.stderr, flush=True)
                else:
                    logger.warning(f'Failed to queue AI analysis task for session {session_id}')
                    print(f'[TASK] ⚠️ Failed to queue AI analysis task', file=sys.stderr, flush=True)
            else:
                # Local development: Use background processing
                from apps.core.services.background_tasks import process_ai_analysis_locally
                logger.info(f'🔵 Triggering local AI analysis for session {session_id}')
                print(f'[TASK] 🔵 Triggering local AI analysis (Cloud Tasks disabled)', file=sys.stderr, flush=True)
                process_ai_analysis_locally(session_id)
            
            # Return success
            return Response({
                'success': True,
                'sessionId': session_id,
                'message': 'Transcription task processed successfully',
                'turnsCount': len(turns)
            }, status=status.HTTP_200_OK)
                    
        except Exception as e:
            import traceback
            print(f'[TASK] ❌ Exception in transcription task: {e}', file=sys.stderr, flush=True)
            print(f'[TASK] Traceback: {traceback.format_exc()}', file=sys.stderr, flush=True)
            logger.error(f'Error in transcription task: {e}', exc_info=True)
            
            # Update session status to failed (not 'error' - database constraint doesn't allow 'error')
            if supabase:
                try:
                    config = settings.APP_SETTINGS.supabase
                    table_name = config.sessions_table
                    supabase.table(table_name).update({
                        'status': 'failed',  # Use 'failed' instead of 'error' to match database constraint
                        'last_event_received_at': format_timestamp()
                    }).eq('id', session_id).execute()
                    logger.info(f'Updated session {session_id} status to failed')
                except Exception as update_error:
                    logger.error(f'Failed to update session status to failed: {update_error}')
            
            # Return error but don't retry (Cloud Tasks will retry on 5xx)
            return Response({
                'success': False,
                'error': str(e),
                'sessionId': session_id
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class GenerateAIAnalysisView(APIView):
    """
    POST /api/tasks/generate-ai-analysis
    Generate AI summary and scorecard for a call.
    
    Body: { sessionId }
    
    Note: This endpoint is called by Google Cloud Tasks.
    Cloud Tasks will include OIDC token authentication and task headers.
    CSRF exempt because Cloud Tasks uses OIDC token authentication.
    """
    permission_classes = [AllowAny]  # Cloud Tasks authenticates via OIDC token
    parser_classes = [JSONParser]
    
    def post(self, request):
        # Log Cloud Tasks headers for debugging
        task_name = request.headers.get('X-CloudTasks-TaskName', 'N/A')
        queue_name = request.headers.get('X-CloudTasks-QueueName', 'N/A')
        print(f'[AI_TASK] 🟢 Cloud Tasks AI analysis request received: taskName={task_name}, queueName={queue_name}', file=sys.stderr, flush=True)
        logger.info(
            f'🟢 Cloud Tasks AI analysis request received: taskName={task_name}, queueName={queue_name}, '
            f'path={request.path}, method={request.method}'
        )
        
        session_id = request.data.get('sessionId')
        
        print(f'[AI_TASK] Request data: sessionId={session_id}', file=sys.stderr, flush=True)
        
        if not session_id:
            print(f'[AI_TASK] ❌ Missing required field: sessionId', file=sys.stderr, flush=True)
            logger.error('Missing required field: sessionId')
            return Response(
                {'error': 'Missing sessionId'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        print(f'[AI_TASK] Received AI analysis task: sessionId={session_id}', file=sys.stderr, flush=True)
        logger.info(f'Received AI analysis task: sessionId={session_id}')
        
        # Update session status to indicate AI analysis is starting
        supabase = get_supabase_client()
        if not supabase:
            logger.error('Supabase client not available for AI analysis task')
            return Response({
                'success': False,
                'sessionId': session_id,
                'error': 'Supabase not available'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        try:
            config = settings.APP_SETTINGS.supabase
            table_name = config.sessions_table
            
            print(f'[AI_TASK] Updating session {session_id} AI analysis status to in_progress', file=sys.stderr, flush=True)
            
            # Update both summary and scorecard status to in_progress
            now = format_timestamp()
            result = supabase.table(table_name).update({
                'call_summary_status': 'in_progress',
                'call_scorecard_status': 'in_progress',
                'analysis_started_at': now,
                'last_event_received_at': now
            }).eq('id', session_id).execute()
            
            print(f'[AI_TASK] ✅ Updated session {session_id} AI analysis status to in_progress. Result: {result}', file=sys.stderr, flush=True)
            logger.info(f'Updated session {session_id} AI analysis status to in_progress')
        except Exception as e:
            logger.error(f'Failed to update AI analysis status: {e}', exc_info=True)
            # Continue anyway - try to generate AI analysis
        
        # Generate AI summary and scorecard using OpenAI
        if supabase:
            try:
                from apps.ai.services import CallSummaryService
                
                # Initialize AI service (with error handling)
                try:
                    ai_service = CallSummaryService()
                except ValueError as e:
                    logger.error(f'Failed to initialize AI service: {e}. OpenAI API key may not be configured.')
                    # Fall back to mock data if OpenAI is not configured
                    ai_service = None
                except Exception as e:
                    logger.error(f'Unexpected error initializing AI service: {e}', exc_info=True)
                    ai_service = None
                
                # If AI service is not available, use mock data
                if not ai_service:
                    logger.warning(f'AI service not available, using mock data for session {session_id}')
                    import time
                    time.sleep(2)  # Simulate processing time
                    
                    config = settings.APP_SETTINGS.supabase
                    table_name = config.sessions_table
                    
                    print(f'[AI_TASK] Using mock data for session {session_id} (AI service not available)', file=sys.stderr, flush=True)
                    
                    # Update to completed (with mock data)
                    now = format_timestamp()
                    result = supabase.table(table_name).update({
                        'call_summary_status': 'completed',
                        'call_scorecard_status': 'completed',
                        'call_summary_generated_at': now,
                        'call_scorecard_generated_at': now,
                        'analysis_completed_at': now,
                        'call_summary_data': {
                            'summary': 'Mock summary - AI service not configured',
                            'key_points': ['Point 1', 'Point 2'],
                            'action_items': []
                        },
                        'call_scorecard_data': {
                            'overall_weighted_score': 85.0,
                            'categories': {}
                        },
                        'last_event_received_at': format_timestamp()
                    }).eq('id', session_id).execute()
                    
                    print(f'[AI_TASK] ✅ Mock AI analysis completed for session {session_id}. Result: {result}', file=sys.stderr, flush=True)
                    logger.info(f'✅ AI analysis completed (mock) for session {session_id}')
                    return Response({
                        'success': True,
                        'sessionId': session_id,
                        'message': 'AI analysis task processed (mock - OpenAI not configured)'
                    }, status=status.HTTP_200_OK)
                
                # Generate summary and scorecard in parallel
                summary_data = None
                scorecard_data = None
                summary_error = None
                scorecard_error = None
                
                # Generate summary
                try:
                    logger.info(f'Generating summary for session {session_id}')
                    summary_data = ai_service.generate_summary(session_id)
                    logger.info(f'✅ Summary generated successfully for session {session_id}')
                except Exception as e:
                    summary_error = str(e)
                    logger.error(f'❌ Summary generation failed for session {session_id}: {e}', exc_info=True)
                    # Update status to failed
                    config = settings.APP_SETTINGS.supabase
                    table_name = config.sessions_table
                    supabase.table(table_name).update({
                        'call_summary_status': 'failed',
                        'call_summary_error': summary_error,
                        'last_event_received_at': format_timestamp()
                    }).eq('id', session_id).execute()
                
                # Generate scorecard
                try:
                    logger.info(f'Generating scorecard for session {session_id}')
                    scorecard_data = ai_service.generate_scorecard(session_id)
                    logger.info(f'✅ Scorecard generated successfully for session {session_id}')
                except Exception as e:
                    scorecard_error = str(e)
                    logger.error(f'❌ Scorecard generation failed for session {session_id}: {e}', exc_info=True)
                    # Update status to failed
                    config = settings.APP_SETTINGS.supabase
                    table_name = config.sessions_table
                    supabase.table(table_name).update({
                        'call_scorecard_status': 'failed',
                        'call_scorecard_error': scorecard_error,
                        'last_event_received_at': format_timestamp()
                    }).eq('id', session_id).execute()
                
                # Update session with results
                config = settings.APP_SETTINGS.supabase
                table_name = config.sessions_table
                
                update_data = {
                    'last_event_received_at': format_timestamp()
                }
                
                # Update summary status and data if available
                now = format_timestamp()
                if summary_data:
                    update_data['call_summary_status'] = 'completed'
                    update_data['call_summary_data'] = summary_data
                    update_data['call_summary_generated_at'] = now
                elif summary_error:
                    update_data['call_summary_status'] = 'failed'
                    update_data['call_summary_error'] = summary_error
                
                # Update scorecard status and data if available
                if scorecard_data:
                    update_data['call_scorecard_status'] = 'completed'
                    update_data['call_scorecard_data'] = scorecard_data
                    update_data['call_scorecard_generated_at'] = now
                elif scorecard_error:
                    update_data['call_scorecard_status'] = 'failed'
                    update_data['call_scorecard_error'] = scorecard_error
                
                # Set analysis_completed_at when both are done (or failed)
                if (summary_data or summary_error) and (scorecard_data or scorecard_error):
                    update_data['analysis_completed_at'] = now
                
                # Only update if we have at least one result
                if summary_data or scorecard_data or summary_error or scorecard_error:
                    print(f'[AI_TASK] Updating session {session_id} with AI analysis results: {update_data}', file=sys.stderr, flush=True)
                    result = supabase.table(table_name).update(update_data).eq('id', session_id).execute()
                    print(f'[AI_TASK] ✅ AI analysis completed for session {session_id}. Result: {result}', file=sys.stderr, flush=True)
                    logger.info(f'✅ AI analysis completed for session {session_id}')
                else:
                    logger.warning(f'No AI analysis results to save for session {session_id}')
                    
            except Exception as e:
                logger.error(f'Error in AI analysis: {e}', exc_info=True)
                # Update both to failed if service initialization failed
                if supabase:
                    try:
                        config = settings.APP_SETTINGS.supabase
                        table_name = config.sessions_table
                        supabase.table(table_name).update({
                            'call_summary_status': 'failed',
                            'call_scorecard_status': 'failed',
                            'call_summary_error': str(e),
                            'call_scorecard_error': str(e),
                            'last_event_received_at': format_timestamp()
                        }).eq('id', session_id).execute()
                    except Exception as update_error:
                        logger.error(f'Failed to update error status: {update_error}', exc_info=True)
        else:
            logger.error('Supabase not available for AI analysis task')
        
        # Always return 200 OK so Cloud Tasks doesn't retry
        # Even if there were errors, we've logged them and updated the status
        return Response({
            'success': True,
            'sessionId': session_id,
            'message': 'AI analysis task processed'
        }, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class StartSpyCallView(APIView):
    """
    POST /api/tasks/start-spy-call
    Initiate a Twilio SPY call for Buffalo PBX call monitoring.

    Body: {
        extension, buffaloCallId, direction, caller, destNum,
        spyNumber, snumber, dnumber, cnumber
    }

    Note: This endpoint is called by Google Cloud Tasks.
    Cloud Tasks will include OIDC token authentication and task headers.
    """
    permission_classes = [AllowAny]  # Cloud Tasks authenticates via OIDC token
    parser_classes = [JSONParser]

    def post(self, request):
        # Log Cloud Tasks headers for debugging
        task_name = request.headers.get('X-CloudTasks-TaskName', 'N/A')
        queue_name = request.headers.get('X-CloudTasks-QueueName', 'N/A')
        print(f'[START-SPY-TASK] 🔵 Cloud Tasks request received: taskName={task_name}, queueName={queue_name}', file=sys.stderr, flush=True)
        logger.info(
            f'[START-SPY-TASK] 🔵 Cloud Tasks request received: taskName={task_name}, queueName={queue_name}, '
            f'path={request.path}, method={request.method}'
        )

        # Extract request data
        extension = request.data.get('extension')
        buffalo_call_id = request.data.get('buffaloCallId')
        direction = request.data.get('direction')
        caller = request.data.get('caller')
        dest_num = request.data.get('destNum')
        spy_number = request.data.get('spyNumber')

        # Validate required fields
        if not extension or not buffalo_call_id:
            logger.error(f'[START-SPY-TASK] Missing required fields: extension={extension}, buffaloCallId={buffalo_call_id}')
            return Response(
                {'error': 'Missing extension or buffaloCallId'},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(
            f'[START-SPY-TASK] Initiating SPY call - Extension={extension}, '
            f'BuffaloCallId={buffalo_call_id}, Direction={direction}'
        )

        # Build call_details dict for initiate_spy_call
        call_details = {
            'callId': buffalo_call_id,
            'direction': direction or 'UNKNOWN',
            'caller': caller or 'Unknown',
            'destNum': dest_num or 'N/A',
            'spyNumber': spy_number or extension,
            'snumber': request.data.get('snumber'),
            'dnumber': request.data.get('dnumber'),
            'cnumber': request.data.get('cnumber'),
        }

        # Call initiate_spy_call service
        from apps.twilio.services import initiate_spy_call

        result = initiate_spy_call(extension, call_details)

        if result['success']:
            logger.info(
                f'[START-SPY-TASK] ✅ SPY call initiated successfully - '
                f'CallSid={result["call_sid"]}, SessionId={result["session_id"]}, '
                f'BuffaloCallId={buffalo_call_id}'
            )
            print(
                f'[START-SPY-TASK] ✅ SPY call initiated - CallSid={result["call_sid"]}, '
                f'SessionId={result["session_id"]}', file=sys.stderr, flush=True
            )
            return Response({
                'success': True,
                'callSid': result['call_sid'],
                'sessionId': result['session_id'],
                'buffaloCallId': buffalo_call_id
            }, status=status.HTTP_200_OK)
        else:
            logger.error(
                f'[START-SPY-TASK] ❌ Failed to initiate SPY call - '
                f'Extension={extension}, BuffaloCallId={buffalo_call_id}, Error={result["error"]}'
            )
            print(
                f'[START-SPY-TASK] ❌ Failed to initiate SPY call: {result["error"]}',
                file=sys.stderr, flush=True
            )
            # Return 500 to trigger Cloud Tasks retry
            return Response({
                'success': False,
                'error': result['error'],
                'buffaloCallId': buffalo_call_id
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class CleanupSpyCallView(APIView):
    """
    POST /api/tasks/cleanup-spy-call
    Cleanup SPY call: hangup, poll for recording, upload, trigger transcription.

    Body: { buffaloCallId }

    Note: This endpoint is called by Google Cloud Tasks.
    Cloud Tasks will include OIDC token authentication and task headers.
    """
    permission_classes = [AllowAny]  # Cloud Tasks authenticates via OIDC token
    parser_classes = [JSONParser]

    def post(self, request):
        # Log Cloud Tasks headers for debugging
        task_name = request.headers.get('X-CloudTasks-TaskName', 'N/A')
        queue_name = request.headers.get('X-CloudTasks-QueueName', 'N/A')
        print(f'[CLEANUP-SPY-TASK] 🔵 Cloud Tasks request received: taskName={task_name}, queueName={queue_name}', file=sys.stderr, flush=True)
        logger.info(
            f'[CLEANUP-SPY-TASK] 🔵 Cloud Tasks request received: taskName={task_name}, queueName={queue_name}, '
            f'path={request.path}, method={request.method}'
        )

        buffalo_call_id = request.data.get('buffaloCallId')

        if not buffalo_call_id:
            logger.error('[CLEANUP-SPY-TASK] Missing required field: buffaloCallId')
            return Response(
                {'error': 'Missing buffaloCallId'},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f'[CLEANUP-SPY-TASK] Starting cleanup for BuffaloCallId={buffalo_call_id}')

        # Get Supabase client
        supabase = get_supabase_client()
        if not supabase:
            logger.error('[CLEANUP-SPY-TASK] Supabase client not available')
            return Response(
                {'error': 'Supabase not available'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        try:
            config = settings.APP_SETTINGS.supabase
            sessions_table = config.sessions_table

            # Step 1: Find session by buffalo_call_id
            result = supabase.table(sessions_table).select(
                'id, call_sid, status, recording_sid, audio_storage_path'
            ).eq('buffalo_call_id', buffalo_call_id).execute()

            if not result.data or len(result.data) == 0:
                logger.info(f'[CLEANUP-SPY-TASK] No SPY call found for BuffaloCallId={buffalo_call_id}')
                return Response({
                    'success': True,
                    'message': 'No SPY call found',
                    'buffaloCallId': buffalo_call_id
                }, status=status.HTTP_200_OK)

            session_data = result.data[0]
            session_id = session_data['id']
            call_sid = session_data.get('call_sid')
            status_value = session_data.get('status')
            existing_recording_sid = session_data.get('recording_sid')
            existing_storage_path = session_data.get('audio_storage_path')

            logger.info(
                f'[CLEANUP-SPY-TASK] Found session - SessionId={session_id}, '
                f'CallSid={call_sid}, Status={status_value}'
            )

            # Check if recording already exists (downloaded by webhook)
            if existing_recording_sid and existing_storage_path:
                logger.info(
                    f'[CLEANUP-SPY-TASK] ✅ Recording already downloaded - '
                    f'RecordingSid={existing_recording_sid}, StoragePath={existing_storage_path}, '
                    f'SessionId={session_id}'
                )
                
                # Check if transcription is already queued or completed
                if status_value in ['recorded', 'transcribed', 'completed']:
                    logger.info(
                        f'[CLEANUP-SPY-TASK] Recording already processed - Status={status_value}, '
                        f'SessionId={session_id}'
                    )
                    return Response({
                        'success': True,
                        'message': 'Recording already processed',
                        'sessionId': session_id,
                        'buffaloCallId': buffalo_call_id,
                        'recordingSid': existing_recording_sid,
                        'storagePath': existing_storage_path
                    }, status=status.HTTP_200_OK)
                
                # Recording exists but transcription not started - trigger transcription
                logger.info(
                    f'[CLEANUP-SPY-TASK] Triggering transcription for existing recording - '
                    f'SessionId={session_id}'
                )
                
                cloud_tasks_config = settings.APP_SETTINGS.cloud_tasks
                
                if cloud_tasks_config.enabled:
                    # Production/Staging: Use Cloud Tasks
                    service_url = os.getenv('CLOUD_RUN_SERVICE_URL')
                    if not service_url:
                        k_service = os.getenv('K_SERVICE')
                        if k_service:
                            service_url = f'https://verc-app-staging-clw2hnetfa-uk.a.run.app'
                        else:
                            service_url = 'https://verc-app-staging-clw2hnetfa-uk.a.run.app'
                    
                    from apps.core.services.cloud_tasks import enqueue_transcription_task
                    transcription_queued = enqueue_transcription_task(session_id, existing_storage_path, service_url)
                    
                    if transcription_queued:
                        logger.info(f'[CLEANUP-SPY-TASK] ✅ Transcription task queued - SessionId={session_id}')
                    else:
                        logger.warning(f'[CLEANUP-SPY-TASK] Failed to queue transcription task')
                else:
                    # Local development: Use background processing
                    from apps.core.services.background_tasks import process_transcription_locally
                    logger.info(f'[CLEANUP-SPY-TASK] 🔵 Triggering local transcription (Cloud Tasks disabled)')
                    process_transcription_locally(session_id, existing_storage_path)
                
                return Response({
                    'success': True,
                    'message': 'Recording already downloaded, transcription triggered',
                    'sessionId': session_id,
                    'buffaloCallId': buffalo_call_id,
                    'recordingSid': existing_recording_sid,
                    'storagePath': existing_storage_path
                }, status=status.HTTP_200_OK)

            if not call_sid:
                logger.warning(f'[CLEANUP-SPY-TASK] Session {session_id} has no call_sid')
                return Response({
                    'success': True,
                    'message': 'Session has no call_sid',
                    'sessionId': session_id
                }, status=status.HTTP_200_OK)

            # Step 2: Hangup the call (if still active)
            if status_value in ['initiated', 'calling', 'in_progress']:
                logger.info(f'[CLEANUP-SPY-TASK] Hanging up call - CallSid={call_sid}')
                from apps.twilio.services import hangup_call

                hangup_result = hangup_call(call_sid, reason='Buffalo PBX call terminated')

                if hangup_result['success']:
                    logger.info(f'[CLEANUP-SPY-TASK] ✅ Call hung up - CallSid={call_sid}')
                else:
                    logger.warning(f'[CLEANUP-SPY-TASK] Failed to hangup call: {hangup_result["error"]}')
            else:
                logger.info(f'[CLEANUP-SPY-TASK] Call already in terminal status: {status_value}')

            # Step 3: Poll Twilio API for recording (10s interval, max 5 minutes)
            import time
            from twilio.rest import Client
            from twilio.base.exceptions import TwilioRestException

            client = Client(
                settings.APP_SETTINGS.twilio.account_sid,
                settings.APP_SETTINGS.twilio.auth_token
            )

            max_poll_time = 300  # 5 minutes
            poll_interval = 10  # 10 seconds
            elapsed_time = 0
            recording_sid = None
            recording_url = None

            logger.info(f'[CLEANUP-SPY-TASK] Polling for recording - CallSid={call_sid}')

            while elapsed_time < max_poll_time:
                try:
                    # Fetch recordings for this call
                    recordings = client.recordings.list(call_sid=call_sid, limit=1)

                    if recordings and len(recordings) > 0:
                        recording = recordings[0]
                        recording_sid = recording.sid
                        recording_url = recording.uri
                        logger.info(
                            f'[CLEANUP-SPY-TASK] ✅ Recording found - RecordingSid={recording_sid}, '
                            f'CallSid={call_sid}'
                        )
                        break

                    # No recording yet, wait and retry
                    time.sleep(poll_interval)
                    elapsed_time += poll_interval
                    logger.debug(f'[CLEANUP-SPY-TASK] No recording yet, elapsed={elapsed_time}s')

                except TwilioRestException as e:
                    logger.error(f'[CLEANUP-SPY-TASK] Twilio API error polling recordings: {e}')
                    break

            if not recording_sid:
                logger.warning(
                    f'[CLEANUP-SPY-TASK] No recording found after {elapsed_time}s - '
                    f'CallSid={call_sid}, SessionId={session_id}'
                )
                # Update session status to indicate no recording
                supabase.table(sessions_table).update({
                    'status': 'completed',
                    'last_event_received_at': format_timestamp()
                }).eq('id', session_id).execute()

                return Response({
                    'success': True,
                    'message': 'No recording found',
                    'sessionId': session_id,
                    'buffaloCallId': buffalo_call_id
                }, status=status.HTTP_200_OK)

            # Step 4: Download recording from Twilio
            logger.info(f'[CLEANUP-SPY-TASK] Downloading recording - RecordingSid={recording_sid}')
            from apps.twilio.services import download_twilio_recording

            download_result = download_twilio_recording(recording_sid, recording_url)

            if not download_result['success']:
                logger.error(f'[CLEANUP-SPY-TASK] Failed to download recording: {download_result["error"]}')
                return Response({
                    'success': False,
                    'error': f'Failed to download recording: {download_result["error"]}',
                    'sessionId': session_id
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            audio_bytes = download_result['audio_bytes']
            content_type = download_result['content_type']

            # Step 5: Upload recording to Supabase Storage
            logger.info(f'[CLEANUP-SPY-TASK] Uploading recording to storage - SessionId={session_id}')
            from apps.twilio.services import upload_recording_to_storage

            upload_result = upload_recording_to_storage(
                session_id, recording_sid, audio_bytes, content_type
            )

            if not upload_result['success']:
                logger.error(f'[CLEANUP-SPY-TASK] Failed to upload recording: {upload_result["error"]}')
                return Response({
                    'success': False,
                    'error': f'Failed to upload recording: {upload_result["error"]}',
                    'sessionId': session_id
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            storage_path = upload_result['storage_path']

            # Step 6: Update session with recording metadata
            logger.info(f'[CLEANUP-SPY-TASK] Updating session with recording metadata - SessionId={session_id}')
            supabase.table(sessions_table).update({
                'recording_sid': recording_sid,
                'audio_storage_path': storage_path,
                'status': 'recorded',
                'last_event_received_at': format_timestamp()
            }).eq('id', session_id).execute()

            # Step 7: Enqueue transcription task (chain to existing pipeline)
            logger.info(f'[CLEANUP-SPY-TASK] Triggering transcription pipeline - SessionId={session_id}')

            cloud_tasks_config = settings.APP_SETTINGS.cloud_tasks

            if cloud_tasks_config.enabled:
                # Production/Staging: Use Cloud Tasks
                service_url = os.getenv('CLOUD_RUN_SERVICE_URL')
                if not service_url:
                    k_service = os.getenv('K_SERVICE')
                    if k_service:
                        service_url = f'https://verc-app-staging-clw2hnetfa-uk.a.run.app'
                    else:
                        service_url = 'https://verc-app-staging-clw2hnetfa-uk.a.run.app'

                from apps.core.services.cloud_tasks import enqueue_transcription_task
                transcription_queued = enqueue_transcription_task(session_id, storage_path, service_url)

                if transcription_queued:
                    logger.info(f'[CLEANUP-SPY-TASK] ✅ Transcription task queued - SessionId={session_id}')
                else:
                    logger.warning(f'[CLEANUP-SPY-TASK] Failed to queue transcription task')
            else:
                # Local development: Use background processing
                from apps.core.services.background_tasks import process_transcription_locally
                logger.info(f'[CLEANUP-SPY-TASK] 🔵 Triggering local transcription (Cloud Tasks disabled)')
                print(f'[CLEANUP-SPY-TASK] 🔵 Triggering local transcription', file=sys.stderr, flush=True)
                process_transcription_locally(session_id, storage_path)

            logger.info(
                f'[CLEANUP-SPY-TASK] ✅ Cleanup completed - SessionId={session_id}, '
                f'BuffaloCallId={buffalo_call_id}, RecordingSid={recording_sid}'
            )

            return Response({
                'success': True,
                'sessionId': session_id,
                'buffaloCallId': buffalo_call_id,
                'recordingSid': recording_sid,
                'storagePath': storage_path,
                'message': 'Cleanup completed, transcription queued'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(
                f'[CLEANUP-SPY-TASK] ❌ Error during cleanup - '
                f'BuffaloCallId={buffalo_call_id}, Error={str(e)}',
                exc_info=True
            )
            return Response({
                'success': False,
                'error': str(e),
                'buffaloCallId': buffalo_call_id
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

