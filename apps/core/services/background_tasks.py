"""
Background task processing for local development.
Provides threading-based async processing when Cloud Tasks is disabled.
"""

import threading
import logging
import httpx

logger = logging.getLogger(__name__)


def process_transcription_locally(session_id: str, storage_path: str) -> None:
    """
    Process transcription in a background thread (for local development).

    This mimics Cloud Tasks behavior but runs locally using threading.
    Calls the transcription endpoint directly.

    Args:
        session_id: The session ID to process
        storage_path: Path to audio file in Supabase Storage
    """

    def run_transcription():
        try:
            logger.info(
                f"[LOCAL_TASK] Starting background transcription for session {session_id}"
            )

            # Call the transcription endpoint directly (local HTTP call)
            url = "http://localhost:8080/api/tasks/transcribe-audio"
            payload = {
                "sessionId": session_id,
                "storagePath": storage_path
            }

            response = httpx.post(url, json=payload, timeout=600.0)
            response.raise_for_status()

            logger.info(
                f"[LOCAL_TASK] ✅ Background transcription completed for session {session_id}"
            )
        except Exception as e:
            logger.error(
                f"[LOCAL_TASK] ❌ Background transcription failed for session {session_id}: {e}",
                exc_info=True,
            )

    # Start transcription in background thread
    thread = threading.Thread(target=run_transcription, daemon=True)
    thread.start()
    logger.info(
        f"[LOCAL_TASK] Background transcription thread started for session {session_id}"
    )


def process_ai_analysis_locally(session_id: str) -> None:
    """
    Process AI analysis in a background thread (for local development).

    This mimics Cloud Tasks behavior but runs locally using threading.
    Calls the AI analysis endpoint directly.

    Args:
        session_id: The session ID to process
    """

    def run_ai_analysis():
        try:
            logger.info(
                f"[LOCAL_TASK] Starting background AI analysis for session {session_id}"
            )

            # Call the AI analysis endpoint directly (local HTTP call)
            url = "http://localhost:8080/api/tasks/generate-ai-analysis"
            payload = {
                "sessionId": session_id
            }

            response = httpx.post(url, json=payload, timeout=600.0)
            response.raise_for_status()

            logger.info(
                f"[LOCAL_TASK] ✅ Background AI analysis completed for session {session_id}"
            )
        except Exception as e:
            logger.error(
                f"[LOCAL_TASK] ❌ Background AI analysis failed for session {session_id}: {e}",
                exc_info=True,
            )

    # Start AI analysis in background thread
    thread = threading.Thread(target=run_ai_analysis, daemon=True)
    thread.start()
    logger.info(
        f"[LOCAL_TASK] Background AI analysis thread started for session {session_id}"
    )
