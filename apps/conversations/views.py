"""
Conversation views for audio upload and transcription management.
"""

import os
import sys
import logging
import uuid
from datetime import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.permissions import AllowAny
from django.conf import settings

from apps.core.services.supabase import get_supabase_client
from apps.core.utils import format_timestamp, retry_on_exception

logger = logging.getLogger(__name__)


class UploadView(APIView):
    """
    POST /api/conversation/upload
    Upload audio file for transcription.
    Uploads file to Supabase Storage, creates session, and queues Cloud Task.
    Frontend expects: { storagePath, audioUrl, originalName, sessionId }
    Returns 202 Accepted if Cloud Task is queued, 200 OK otherwise.
    """

    permission_classes = [AllowAny]  # Allow access with mock tokens
    parser_classes = [MultiPartParser]

    def post(self, request):
        try:
            audio_file = request.FILES.get("audio")

            if not audio_file:
                return Response(
                    {"error": "No audio file provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            logger.info(
                f"Received audio file upload: {audio_file.name} ({audio_file.size} bytes)"
            )

            # Upload to Supabase Storage
            supabase = get_supabase_client()
            if not supabase:
                logger.error("Supabase client not available, cannot upload audio file")
                return Response(
                    {"error": "Storage service not available"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            from django.conf import settings

            config = settings.APP_SETTINGS.supabase
            bucket = config.audio_bucket

            # Generate storage path: orgId/userId/timestamp-filename
            # For now, use a simple path since we don't have user/org context yet
            timestamp = int(datetime.utcnow().timestamp() * 1000)
            sanitized_name = audio_file.name.replace("/", "_").replace("\\", "_")
            storage_path = f"{uuid.uuid4()}/{timestamp}-{sanitized_name}"

            # Read file content as bytes
            audio_file.seek(0)  # Reset file pointer
            file_content = audio_file.read()

            # Ensure file_content is bytes
            if isinstance(file_content, str):
                file_content = file_content.encode("utf-8")
            elif not isinstance(file_content, bytes):
                file_content = bytes(file_content)

            # Upload to Supabase Storage
            try:
                # Supabase Python client upload signature: upload(path, file, file_options={})
                # For supabase-py 1.2.0, file_options should only contain content-type
                # upsert is not supported in this version, so we'll handle conflicts by using unique paths
                upload_response = supabase.storage.from_(bucket).upload(
                    storage_path,
                    file_content,
                    file_options={
                        "content-type": audio_file.content_type or "audio/mpeg"
                    },
                )

                # Supabase Python client returns a response object with .data and .error attributes
                if hasattr(upload_response, "error") and upload_response.error:
                    raise Exception(f"Storage upload failed: {upload_response.error}")

                logger.info(
                    f"✅ Audio file uploaded to Supabase Storage: {storage_path}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to upload to Supabase Storage: {e}", exc_info=True
                )
                return Response(
                    {"error": f"Failed to upload file to storage: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Generate signed URL for immediate playback
            signed_url = None
            try:
                signed_url_response = supabase.storage.from_(bucket).create_signed_url(
                    storage_path, expires_in=3600  # 1 hour
                )

                # Handle different response formats from Supabase client
                if hasattr(signed_url_response, "error") and signed_url_response.error:
                    logger.warning(
                        f"Failed to generate signed URL: {signed_url_response.error}"
                    )
                elif hasattr(signed_url_response, "signedURL"):
                    signed_url = signed_url_response.signedURL
                elif hasattr(signed_url_response, "data"):
                    data = signed_url_response.data
                    signed_url = (
                        data.get("signedURL")
                        if isinstance(data, dict)
                        else getattr(data, "signedURL", None)
                    )

                if signed_url:
                    logger.info(f"Generated signed URL for {storage_path}")
            except Exception as e:
                logger.warning(f"Failed to generate signed URL: {e}")

            # Generate session ID
            session_id = str(uuid.uuid4())

            # Create session in Supabase
            now = format_timestamp()
            try:
                table_name = config.sessions_table
                # Extract user_id and org_id from request if available (for authenticated requests)
                user_id = None
                org_id = None
                # Note: Currently upload endpoint doesn't require auth, but we can extract from headers if available
                # This will be None for now, but structure is ready for when auth is added

                session_data = {
                    "id": session_id,
                    "created_at": now,
                    "last_event_received_at": now,
                    "status": "created",
                    "call_summary_status": "not_started",
                    "call_scorecard_status": "not_started",
                    "audio_storage_path": storage_path,
                    "metadata": {
                        "source": "audio-upload",
                        "originalName": audio_file.name,
                        "storagePath": storage_path,
                        "uploadedAt": now,
                    },
                    "caller_number": None,
                    "dialed_number": None,
                    "user_id": user_id,
                    "org_id": org_id,
                }

                supabase.table(table_name).insert(session_data).execute()
                logger.info(
                    f"✅ Created transcription session {session_id} in Supabase"
                )
            except Exception as e:
                logger.error(
                    f"Failed to create session in Supabase: {e}", exc_info=True
                )
                # Continue anyway - session creation failure shouldn't block upload

            # Queue Cloud Task if enabled
            cloud_tasks_config = settings.APP_SETTINGS.cloud_tasks
            # Use print to stderr for guaranteed visibility in Cloud Run logs
            print(
                f"[UPLOAD] Cloud Tasks config: enabled={cloud_tasks_config.enabled}, project_id={cloud_tasks_config.project_id}, region={cloud_tasks_config.region}, queue_name={cloud_tasks_config.queue_name}",
                file=sys.stderr,
                flush=True,
            )
            logger.info(
                f"🔵 Cloud Tasks config: enabled={cloud_tasks_config.enabled}, "
                f"project_id={cloud_tasks_config.project_id}, region={cloud_tasks_config.region}, "
                f"queue_name={cloud_tasks_config.queue_name}, "
                f"service_account={cloud_tasks_config.service_account_email}"
            )

            if cloud_tasks_config.enabled:
                try:
                    from apps.core.services.cloud_tasks import (
                        enqueue_transcription_task,
                        get_cloud_tasks_client,
                    )

                    # Test if client can be created
                    test_client = get_cloud_tasks_client()
                    if not test_client:
                        logger.error(
                            "❌ Cloud Tasks client creation failed - cannot queue task"
                        )
                    else:
                        logger.info("✅ Cloud Tasks client created successfully")

                    # Get service URL for Cloud Tasks
                    service_url = os.getenv("CLOUD_RUN_SERVICE_URL")
                    if not service_url:
                        k_service = os.getenv("K_SERVICE")
                        if k_service:
                            service_url = request.build_absolute_uri("/").rstrip("/")
                            logger.info(
                                f"Using request host as Cloud Run service URL: {service_url}"
                            )
                        else:
                            service_url = request.build_absolute_uri("/").rstrip("/")
                            logger.warning(
                                f"CLOUD_RUN_SERVICE_URL not set and not in Cloud Run. Using request host: {service_url}. "
                                "Cloud Tasks will fail if this is not the actual Cloud Run service URL."
                            )

                    print(
                        f"[UPLOAD] Attempting to queue transcription task: sessionId={session_id}, storagePath={storage_path}, serviceUrl={service_url}",
                        file=sys.stderr,
                        flush=True,
                    )
                    logger.info(
                        f"🔵 Attempting to queue transcription task: sessionId={session_id}, storagePath={storage_path}, serviceUrl={service_url}"
                    )

                    task_queued = enqueue_transcription_task(
                        session_id=session_id,
                        storage_path=storage_path,
                        service_url=service_url,
                    )

                    print(
                        f"[UPLOAD] Task queued result: {task_queued}",
                        file=sys.stderr,
                        flush=True,
                    )
                    if task_queued:
                        print(
                            f"[UPLOAD] ✅ Transcription task queued successfully for session {session_id}",
                            file=sys.stderr,
                            flush=True,
                        )
                        logger.info(
                            f"✅ Transcription task queued successfully for session {session_id}"
                        )
                        return Response(
                            {
                                "sessionId": session_id,
                                "storagePath": storage_path,
                                "audioUrl": signed_url
                                or f'https://{config.url.replace("https://", "").split(".")[0]}.supabase.co/storage/v1/object/public/{bucket}/{storage_path}',
                                "originalName": audio_file.name,
                                "message": "Audio uploaded successfully. Transcription queued.",
                            },
                            status=status.HTTP_202_ACCEPTED,
                        )  # 202 Accepted for async processing
                    else:
                        logger.error(
                            f"❌ Failed to queue transcription task for session {session_id}. "
                            f"Cloud Tasks enabled={cloud_tasks_config.enabled}, "
                            f"project_id={cloud_tasks_config.project_id}, "
                            f"region={cloud_tasks_config.region}, "
                            f"queue_name={cloud_tasks_config.queue_name}, "
                            f"service_url={service_url}"
                        )
                        # Continue and return 200 - upload succeeded even if task queueing failed
                        return Response(
                            {
                                "sessionId": session_id,
                                "storagePath": storage_path,
                                "audioUrl": signed_url
                                or f'https://{config.url.replace("https://", "").split(".")[0]}.supabase.co/storage/v1/object/public/{bucket}/{storage_path}',
                                "originalName": audio_file.name,
                                "message": "Audio uploaded successfully, but transcription task queueing failed. Check logs.",
                                "warning": "Task queueing failed",
                            },
                            status=status.HTTP_200_OK,
                        )
                except Exception as e:
                    logger.error(
                        f"❌ Exception while queuing Cloud Task: {e}", exc_info=True
                    )
                    # Continue and return 200 - upload succeeded even if task queueing failed
                    return Response(
                        {
                            "sessionId": session_id,
                            "storagePath": storage_path,
                            "audioUrl": signed_url
                            or f'https://{config.url.replace("https://", "").split(".")[0]}.supabase.co/storage/v1/object/public/{bucket}/{storage_path}',
                            "originalName": audio_file.name,
                            "message": "Audio uploaded successfully, but transcription task queueing failed with exception.",
                            "warning": "Task queueing failed",
                        },
                        status=status.HTTP_200_OK,
                    )
            else:
                # Cloud Tasks disabled - use local background processing
                logger.info("🔵 Cloud Tasks disabled - triggering local background transcription")
                from apps.core.services.background_tasks import process_transcription_locally
                process_transcription_locally(session_id, storage_path)

                # Return 202 Accepted (same as Cloud Tasks would)
                return Response(
                    {
                        "sessionId": session_id,
                        "storagePath": storage_path,
                        "audioUrl": signed_url
                        or f'https://{config.url.replace("https://", "").split(".")[0]}.supabase.co/storage/v1/object/public/{bucket}/{storage_path}',
                        "originalName": audio_file.name,
                        "message": "Audio uploaded successfully. Transcription queued (local processing).",
                    },
                    status=status.HTTP_202_ACCEPTED,
                )

        except Exception as e:
            logger.error(f"Error handling audio upload: {e}", exc_info=True)
            return Response(
                {"error": f"Upload failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SimulateView(APIView):
    """
    POST /api/conversation/simulate
    Simulate conversation from audio file.
    Creates a transcription session in Supabase and returns the session ID.
    Frontend expects: { simulationId } (which is the session ID)
    """

    permission_classes = [AllowAny]  # Allow access with mock tokens
    parser_classes = [JSONParser]

    def post(self, request):
        try:
            storage_path = request.data.get("storagePath", "")
            original_name = request.data.get("originalName", "audio.wav")
            logger.info(f"Starting conversation simulation for: {storage_path}")

            # Generate session ID
            session_id = str(uuid.uuid4())

            # Create session in Supabase
            supabase = get_supabase_client()
            if supabase:
                try:
                    config = settings.APP_SETTINGS.supabase
                    table_name = config.sessions_table

                    now = format_timestamp()

                    # Create session with initial status
                    # Note: user_id and org_id are optional - service_role can insert without them
                    # In production, these would come from the authenticated user's JWT token
                    session_data = {
                        "id": session_id,
                        "created_at": now,
                        "last_event_received_at": now,
                        "status": "created",  # Will be updated to 'transcribing' when transcription starts
                        "call_summary_status": "not_started",
                        "call_scorecard_status": "not_started",
                        "audio_storage_path": storage_path,
                        "metadata": {
                            "source": "audio-upload",
                            "originalName": original_name,
                            "storagePath": storage_path,
                            "uploadedAt": now,
                        },
                        "caller_number": None,  # Audio uploads don't have phone numbers
                        "dialed_number": None,
                        # user_id and org_id are optional - can be NULL for service_role inserts
                        # In production, extract from JWT token
                    }

                    response = supabase.table(table_name).insert(session_data).execute()

                    logger.info(
                        f"Created transcription session {session_id} in Supabase"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to create session in Supabase: {e}", exc_info=True
                    )
                    # Continue anyway - return session ID even if DB insert fails
            else:
                logger.warning(
                    "Supabase not available, session not persisted to database"
                )

            # Queue transcription task if Cloud Tasks is enabled
            config = settings.APP_SETTINGS.cloud_tasks

            logger.info(
                f"Cloud Tasks config check: enabled={config.enabled}, "
                f"project_id={config.project_id}, region={config.region}, "
                f"queue_name={config.queue_name}, service_account={bool(config.service_account_email)}"
            )

            if config.enabled:
                from apps.core.services.cloud_tasks import enqueue_transcription_task

                # Get service URL for Cloud Tasks
                # In Cloud Run, this should be the service URL (not localhost)
                # Priority:
                # 1. CLOUD_RUN_SERVICE_URL env var (explicit - best for production)
                # 2. Request host when running in Cloud Run (K_SERVICE is set)
                # 3. Construct from K_SERVICE + project (fallback)
                # 4. Request host (local testing - won't work for Cloud Tasks)
                service_url = os.getenv("CLOUD_RUN_SERVICE_URL")

                if not service_url:
                    # Check if we're running in Cloud Run
                    k_service = os.getenv("K_SERVICE")

                    if k_service:
                        # In Cloud Run, use the request host (most reliable)
                        # Cloud Run sets the correct Host header
                        service_url = request.build_absolute_uri("/").rstrip("/")
                        logger.info(
                            f"Using request host as Cloud Run service URL: {service_url}"
                        )
                    else:
                        # Local development - request host won't work for Cloud Tasks
                        service_url = request.build_absolute_uri("/").rstrip("/")
                        logger.warning(
                            f"CLOUD_RUN_SERVICE_URL not set and not in Cloud Run. Using request host: {service_url}. "
                            "Cloud Tasks will fail if this is not the actual Cloud Run service URL. "
                            "Set CLOUD_RUN_SERVICE_URL in your .env for local testing."
                        )

                logger.info(f"Using service URL for Cloud Tasks: {service_url}")

                task_queued = enqueue_transcription_task(
                    session_id=session_id,
                    storage_path=storage_path,
                    service_url=service_url,
                )

                if task_queued:
                    logger.info(
                        f"✅ Transcription task queued successfully for session {session_id}"
                    )
                    return Response(
                        {
                            "simulationId": session_id,
                            "message": "Session created and transcription task queued",
                        },
                        status=status.HTTP_202_ACCEPTED,
                    )  # 202 Accepted for async processing
                else:
                    logger.error(
                        f"❌ Failed to queue transcription task for session {session_id}. "
                        "Check logs above for authentication or configuration errors."
                    )
                    # Continue and return 200 - session was created even if task queueing failed
                    # This allows the frontend to work even if Cloud Tasks fails
            else:
                # Cloud Tasks disabled - use local background processing
                logger.info("🔵 Cloud Tasks disabled - triggering local background transcription")
                from apps.core.services.background_tasks import process_transcription_locally
                process_transcription_locally(session_id, storage_path)

            # Return session ID
            return Response(
                {
                    "simulationId": session_id,  # Frontend expects this as the session ID
                    "message": "Simulation started and transcription queued (local processing)" if not config.enabled else "Simulation started (session created)",
                },
                status=status.HTTP_202_ACCEPTED if not config.enabled else status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error starting simulation: {e}", exc_info=True)
            return Response(
                {"error": f"Simulation failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SignedUrlView(APIView):
    """
    GET /api/conversation/audio/signed-url?storagePath=...
    Get signed URL for audio file.
    Frontend expects: { signedUrl }
    """

    permission_classes = [AllowAny]  # Allow access with mock tokens

    @staticmethod
    @retry_on_exception(max_attempts=3, backoff_base=0.5)
    def _create_signed_url_with_retry(supabase, bucket: str, storage_path: str, expires_in: int):
        """
        Create signed URL with retry logic for transient failures.

        This method is wrapped with retry decorator to handle:
        - Connection timeouts
        - Network errors
        - Cold-start Supabase Storage API delays

        Args:
            supabase: Supabase client instance
            bucket: Storage bucket name
            storage_path: Path to file in storage
            expires_in: URL expiration time in seconds

        Returns:
            Signed URL response from Supabase
        """
        return supabase.storage.from_(bucket).create_signed_url(storage_path, expires_in=expires_in)

    def get(self, request):
        storage_path = request.query_params.get("storagePath", "")
        logger.info(f"Requesting signed URL for: {storage_path}")

        if not storage_path:
            return Response(
                {"error": "storagePath parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        supabase = get_supabase_client()
        if not supabase:
            logger.warning("Supabase client not available")
            return Response(
                {"error": "Supabase client not available"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            config = settings.APP_SETTINGS.supabase
            bucket = config.audio_bucket

            # Generate signed URL (1 hour expiry) with automatic retry on failures
            signed_url_response = self._create_signed_url_with_retry(
                supabase, bucket, storage_path, expires_in=3600
            )

            # Debug logging to see actual response format
            import sys

            print(
                f"[SIGNED_URL] Response type: {type(signed_url_response)}",
                file=sys.stderr,
                flush=True,
            )
            print(
                f"[SIGNED_URL] Response: {repr(signed_url_response)[:500]}",
                file=sys.stderr,
                flush=True,
            )

            # Handle different response formats
            signed_url = None

            # Check for error first
            if hasattr(signed_url_response, "error") and signed_url_response.error:
                logger.warning(
                    f"Failed to generate signed URL: {signed_url_response.error}"
                )
                return Response(
                    {
                        "error": f"Failed to generate signed URL: {signed_url_response.error}"
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Try different response formats
            # Format 1: Direct dict response
            if isinstance(signed_url_response, dict):
                signed_url = (
                    signed_url_response.get("signedURL")
                    or signed_url_response.get("signedUrl")
                    or signed_url_response.get("signed_url")
                )
                print(
                    f"[SIGNED_URL] Dict format, keys: {list(signed_url_response.keys())}",
                    file=sys.stderr,
                    flush=True,
                )
            # Format 2: Object with .data attribute
            elif hasattr(signed_url_response, "data"):
                data = signed_url_response.data
                if isinstance(data, dict):
                    signed_url = (
                        data.get("signedURL")
                        or data.get("signedUrl")
                        or data.get("signed_url")
                    )
                    print(
                        f"[SIGNED_URL] Data dict format, keys: {list(data.keys())}",
                        file=sys.stderr,
                        flush=True,
                    )
                else:
                    signed_url = (
                        getattr(data, "signedURL", None)
                        or getattr(data, "signedUrl", None)
                        or getattr(data, "signed_url", None)
                    )
            # Format 3: Direct attribute
            elif hasattr(signed_url_response, "signedURL"):
                signed_url = signed_url_response.signedURL
            elif hasattr(signed_url_response, "signedUrl"):
                signed_url = signed_url_response.signedUrl
            elif hasattr(signed_url_response, "signed_url"):
                signed_url = signed_url_response.signed_url

            if not signed_url:
                logger.error(
                    f"Failed to extract signed URL from response. "
                    f"Type: {type(signed_url_response)}, Repr: {repr(signed_url_response)[:200]}"
                )
                print(
                    f"[SIGNED_URL] ERROR: Could not find signed URL in response",
                    file=sys.stderr,
                    flush=True,
                )
                return Response(
                    {
                        "error": "Failed to generate signed URL - unexpected response format"
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            logger.info(f"✅ Generated signed URL successfully")
            print(f"[SIGNED_URL] SUCCESS: Extracted URL", file=sys.stderr, flush=True)
            # Frontend expects { url: string } format (see types.ts:114)
            return Response(
                {"url": signed_url},  # Changed from 'signedUrl' to 'url'
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error generating signed URL: {e}", exc_info=True)
            import traceback

            print(
                f"[SIGNED_URL] EXCEPTION: {traceback.format_exc()}",
                file=sys.stderr,
                flush=True,
            )
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
