"""
Transcription service using AssemblyAI for audio transcription with speaker diarization.
"""
import logging
from typing import List, Dict, Any, Optional, Union
from django.conf import settings
import assemblyai as aai

logger = logging.getLogger(__name__)


class AssemblyAIProvider:
    """
    AssemblyAI transcription provider with speaker diarization and PII redaction.
    """
    
    def __init__(self):
        """Initialize AssemblyAI client."""
        config = settings.APP_SETTINGS.ai
        
        if not config.assemblyai_api_key:
            raise ValueError("AssemblyAI API key not configured")
        
        # Set API key globally for AssemblyAI SDK
        aai.settings.api_key = config.assemblyai_api_key
        
        # PII redaction configuration
        self.pii_redaction_enabled = config.assemblyai_pii_redaction_enabled
        self.pii_substitution = config.assemblyai_pii_substitution
        self.generate_redacted_audio = config.assemblyai_generate_redacted_audio
        
        logger.info(
            f'AssemblyAI provider initialized: '
            f'pii_redaction={self.pii_redaction_enabled}, '
            f'pii_substitution={self.pii_substitution}, '
            f'generate_redacted_audio={self.generate_redacted_audio}'
        )
    
    def is_ready(self) -> bool:
        """Check if provider is ready to use."""
        return aai.settings.api_key is not None
    
    def transcribe_with_diarization(
        self,
        audio_url: str,
        speaker_mapping: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Transcribe audio with speaker diarization.
        
        Args:
            audio_url: URL to the audio file (can be signed URL from Supabase Storage)
            speaker_mapping: Optional mapping of speaker labels (e.g., {'A': 'agent', 'B': 'customer'})
            
        Returns:
            List of conversation turns with speaker, text, timestamps, etc.
        """
        if not self.is_ready():
            raise ValueError("AssemblyAI provider not initialized")
        
        if not speaker_mapping:
            speaker_mapping = {'A': 'agent', 'B': 'customer'}
        
        logger.info(f'Starting AssemblyAI transcription: audio_url={audio_url[:100]}...')
        
        # Define PII policies for debt collection compliance
        # Using only valid AssemblyAI policy names from their supported list
        # Excludes 'money_amount' per requirement (keep debt amounts visible)
        # Same as old backend implementation
        pii_policies = [
            'person_name',
            'phone_number',
            'email_address',
            'credit_card_number',
            'credit_card_cvv',
            'banking_information',
            'us_social_security_number',
            'date_of_birth',
            'drivers_license',
            'medical_condition',
            'drug',
            'passport_number',
            'location',  # Changed from 'location_address' - see docs
            'account_number'
        ]
        
        logger.info(
            f'PII redaction configuration: enabled={self.pii_redaction_enabled}, '
            f'substitution={self.pii_substitution}, '
            f'generate_redacted_audio={self.generate_redacted_audio}, '
            f'policies_count={len(pii_policies)}'
        )
        
        try:
            # Create transcriber instance
            transcriber = aai.Transcriber()
            
            # Build transcription options dict - similar to old backend's approach
            # Old backend uses: this.client.transcripts.transcribe({ audio, speaker_labels, ... })
            # Python SDK uses: transcriber.transcribe(url, config=TranscriptionConfig(...))
            config_kwargs = {
                'speaker_labels': True,
                'sentiment_analysis': True,
            }
            
            # Add PII redaction parameters only if enabled (same as old backend)
            if self.pii_redaction_enabled:
                config_kwargs['redact_pii'] = True
                config_kwargs['redact_pii_policies'] = pii_policies  # List of strings
                if self.pii_substitution:
                    config_kwargs['redact_pii_sub'] = self.pii_substitution
                if self.generate_redacted_audio:
                    config_kwargs['redact_pii_audio'] = True
            
            # Create config object
            config = aai.TranscriptionConfig(**config_kwargs)
            
            logger.info(f'Starting AssemblyAI transcription for URL: {audio_url[:100]}...')
            
            # Transcribe audio (this will poll until complete)
            # The transcribe method handles polling internally, similar to old backend's await
            try:
                transcript = transcriber.transcribe(audio_url, config=config)
            except Exception as transcribe_error:
                logger.error(f'AssemblyAI transcribe() call failed: {transcribe_error}', exc_info=True)
                raise Exception(f"AssemblyAI transcription submission failed: {str(transcribe_error)}")
            
            # Check if transcription completed successfully
            if not transcript:
                raise Exception("Transcription returned None - check audio URL accessibility")
            
            # Check status - old backend checks: transcript.status === 'error'
            if hasattr(transcript, 'status'):
                if transcript.status == aai.TranscriptStatus.error:
                    error_msg = getattr(transcript, 'error', 'Unknown error')
                    raise Exception(f"Transcription failed with error: {error_msg}")
                elif transcript.status != aai.TranscriptStatus.completed:
                    raise Exception(f"Transcription did not complete. Status: {transcript.status}")
            
            logger.info(
                f'Transcription completed: transcript_id={transcript.id}, '
                f'utterances={len(transcript.utterances) if transcript.utterances else 0}'
            )
            
            # Convert to conversation turns
            turns = self._convert_to_conversation_turns(
                transcript,
                speaker_mapping
            )

            # AssemblyAI provides audio_duration in transcript object (in seconds)
            duration_seconds = None
            if hasattr(transcript, 'audio_duration') and transcript.audio_duration:
                duration_seconds = round(transcript.audio_duration, 2)
                logger.info(f'Audio duration from AssemblyAI: {duration_seconds}s')

            # Return in same format as Modal provider
            return {
                'turns': turns,
                'duration_seconds': duration_seconds,
                'audio_metadata': {
                    'provider': 'assemblyai',
                    'transcript_id': transcript.id if hasattr(transcript, 'id') else None
                }
            }
            
        except Exception as e:
            logger.error(f'Failed to transcribe audio: {e}', exc_info=True)
            raise
    
    def _convert_to_conversation_turns(
        self,
        transcript: aai.Transcript,
        speaker_mapping: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Convert AssemblyAI transcript to conversation turns format.
        
        Args:
            transcript: AssemblyAI transcript object
            speaker_mapping: Mapping of speaker labels to roles
            
        Returns:
            List of conversation turns
        """
        if not transcript.utterances:
            logger.warning('No utterances found in transcription')
            return []
        
        turns = []
        
        # Get sentiment analysis results if available
        sentiment_results = {}
        if hasattr(transcript, 'sentiment_analysis_results') and transcript.sentiment_analysis_results:
            for result in transcript.sentiment_analysis_results:
                if hasattr(result, 'text') and hasattr(result, 'sentiment'):
                    sentiment_results[result.text] = result.sentiment
        
        for utterance in transcript.utterances:
            # Map speaker label to role (utterance.speaker is typically 'A', 'B', etc.)
            speaker_label = utterance.speaker if hasattr(utterance, 'speaker') else None
            speaker_role = speaker_mapping.get(speaker_label, 'unknown') if speaker_label else 'unknown'
            
            # Extract sentiment from utterance text
            sentiment = None
            if utterance.text and utterance.text in sentiment_results:
                sentiment = sentiment_results[utterance.text]
            elif hasattr(utterance, 'sentiment'):
                sentiment = utterance.sentiment
            
            # Extract PII entities if available
            pii_entities = []
            if hasattr(transcript, 'entities') and transcript.entities:
                for entity in transcript.entities:
                    if hasattr(entity, 'entity_type'):
                        pii_entities.append(str(entity.entity_type))
            
            # Calculate timestamps (utterance.start and utterance.end are in seconds, convert to milliseconds)
            start_time_ms = int(utterance.start * 1000) if hasattr(utterance, 'start') and utterance.start is not None else None
            end_time_ms = int(utterance.end * 1000) if hasattr(utterance, 'end') and utterance.end is not None else None
            
            if start_time_ms and end_time_ms:
                duration_ms = end_time_ms - start_time_ms
            else:
                duration_ms = None
            
            turn = {
                'speaker': speaker_role,
                'text': utterance.text if hasattr(utterance, 'text') else '',
                'timestamp': None,  # Will be set based on start_time_ms in the view
                'start_time_ms': start_time_ms,
                'end_time_ms': end_time_ms,
                'duration_ms': duration_ms,
                'confidence': utterance.confidence if hasattr(utterance, 'confidence') else None,
                'sentiment': sentiment,
                'pii_redacted': self.pii_redaction_enabled,
                'pii_entities_detected': pii_entities if pii_entities else None,
                'metadata': {
                    'speaker_label': speaker_label,
                    'transcript_id': transcript.id
                }
            }
            
            # Add redacted audio URL if available
            if self.generate_redacted_audio and hasattr(transcript, 'redacted_audio_url') and transcript.redacted_audio_url:
                turn['redacted_audio_url'] = transcript.redacted_audio_url
            
            turns.append(turn)
        
        logger.info(f'Converted {len(turns)} utterances to conversation turns')
        return turns


class ModalCanaryProvider:
    """
    Modal NVIDIA Canary transcription provider with speaker diarization and PII redaction.
    Uses Modal Labs serverless platform to run NVIDIA Canary Qwen 2.5B STT model.
    """

    def __init__(self):
        """Initialize Modal client."""
        config = settings.APP_SETTINGS.ai

        if not config.modal_enabled:
            raise ValueError("Modal provider is not enabled")

        if not config.modal_app_name:
            raise ValueError("Modal app name not configured")

        self.modal_app_name = config.modal_app_name

        # Modal authentication is set at Django startup in settings/base.py
        # This ensures Modal SDK loads with correct workspace/auth before any imports
        logger.info(
            f'Modal Canary provider initialized: '
            f'app_name={self.modal_app_name}'
        )

    def is_ready(self) -> bool:
        """Check if provider is ready to use."""
        config = settings.APP_SETTINGS.ai
        return config.modal_enabled and bool(config.modal_app_name)

    def transcribe_with_diarization(
        self,
        audio_url: str,
        speaker_mapping: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Transcribe audio with speaker diarization using Modal NVIDIA Canary.

        Args:
            audio_url: URL to the audio file (signed URL from Supabase Storage)
            speaker_mapping: Optional mapping of speaker labels (e.g., {'Speaker1': 'agent', 'Speaker2': 'customer'})

        Returns:
            List of conversation turns with speaker, text, timestamps, etc.
        """
        import modal
        import httpx
        import soundfile as sf
        import tempfile
        import os

        if not self.is_ready():
            raise ValueError("Modal provider not initialized")

        # Don't assume speaker roles - keep Modal's labels as-is
        if not speaker_mapping:
            speaker_mapping = {'Speaker1': 'Speaker1', 'Speaker2': 'Speaker2'}

        logger.info(f'Starting Modal Canary transcription: audio_url={audio_url[:100]}...')

        try:
            # Step 1: Download audio file from signed URL
            logger.info(f'Downloading audio from signed URL...')
            response = httpx.get(audio_url, timeout=60.0)
            response.raise_for_status()

            # Step 2: Save to temporary file and read with soundfile
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(response.content)
                temp_path = temp_file.name

            try:
                logger.info(f'Reading audio file with soundfile...')
                audio_array, sample_rate = sf.read(temp_path)

                # Calculate audio duration in seconds
                duration_seconds = len(audio_array) / sample_rate
                logger.info(f'Audio duration: {duration_seconds:.2f} seconds')

                # Step 3: Call Modal NVIDIA Canary model
                logger.info(f'Calling Modal Canary model: app={self.modal_app_name}')

                # Debug: Check Modal config
                import os as debug_os
                logger.info(f'Modal profile: {debug_os.getenv("MODAL_PROFILE")}')

                # Modal profile is set globally in Django settings (config/settings/base.py)
                # This ensures Modal SDK uses the correct credentials from ~/.modal.toml

                # Try to lookup the app first, then get the class
                # With MODAL_PROFILE set, Modal SDK will use credentials from ~/.modal.toml
                try:
                    CanaryModel = modal.Cls.from_name(
                        self.modal_app_name,
                        "CanaryModel"
                    )
                    logger.info(f'Modal app lookup result: {CanaryModel}')
                    logger.info(f'Modal app type: {type(CanaryModel)}')
                except Exception as lookup_error:
                    logger.error(f'Failed to lookup Modal app: {lookup_error}', exc_info=True)
                    raise Exception(f"Modal app lookup failed: {lookup_error}")

                if CanaryModel is None:
                    raise Exception(f"Modal app '{self.modal_app_name}' returned None. Check app name and authentication.")

                # Instantiate the Modal class
                try:
                    model = CanaryModel()
                    logger.info(f'Modal model instance: {model}')
                    logger.info(f'Modal model type: {type(model)}')
                except Exception as instantiation_error:
                    logger.error(f'Failed to instantiate Modal class: {instantiation_error}', exc_info=True)
                    raise Exception(f"Modal class instantiation failed: {instantiation_error}")

                # Call the transcribe method
                try:
                    result = model.transcribe.remote({
                        "array": audio_array.tolist(),  # Convert numpy array to list for serialization
                        "sampling_rate": int(sample_rate)
                    })
                except Exception as remote_error:
                    logger.error(f'Failed to call Modal remote method: {remote_error}', exc_info=True)
                    raise Exception(f"Modal remote call failed: {remote_error}")

                logger.info(f'Modal transcription completed: {len(result.get("segments", []))} segments')

                # Step 4: Convert to conversation turns format
                turns = self._convert_to_conversation_turns(result, speaker_mapping)

                # Return turns with duration metadata
                return {
                    'turns': turns,
                    'duration_seconds': round(duration_seconds, 2),
                    'audio_metadata': {
                        'sample_rate': int(sample_rate),
                        'total_samples': len(audio_array)
                    }
                }

            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            logger.error(f'Failed to transcribe audio with Modal: {e}', exc_info=True)
            raise

    def _convert_to_conversation_turns(
        self,
        modal_result: Dict[str, Any],
        speaker_mapping: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Convert Modal Canary result to conversation turns format.

        Args:
            modal_result: Modal result with 'full_text' and 'segments'
            speaker_mapping: Mapping of speaker labels to roles

        Returns:
            List of conversation turns
        """
        segments = modal_result.get('segments', [])

        if not segments:
            logger.warning('No segments found in Modal transcription')
            return []

        turns = []

        for segment in segments:
            # Extract segment data - keep Modal's speaker labels as-is
            speaker = segment.get('speaker', 'unknown')

            # Convert timestamps from seconds to milliseconds
            start_time_ms = int(segment.get('start', 0) * 1000)
            end_time_ms = int(segment.get('end', 0) * 1000)
            duration_ms = end_time_ms - start_time_ms

            turn = {
                'speaker': speaker,
                'text': segment.get('text', ''),
                'timestamp': None,  # Will be set based on start_time_ms in the view
                'start_time_ms': start_time_ms,
                'end_time_ms': end_time_ms,
                'duration_ms': duration_ms,
                'confidence': None,  # Modal doesn't provide confidence scores
                'sentiment': None,  # Modal doesn't provide sentiment (handled by OpenAI later)
                'pii_redacted': True,  # Modal does PII redaction with <PERSON>, <DATE_TIME> tags
                'pii_entities_detected': self._extract_pii_entities(segment.get('text', '')),
                'metadata': {
                    'speaker_label': speaker,
                    'provider': 'modal_canary'
                }
            }

            turns.append(turn)

        logger.info(f'Converted {len(turns)} Modal segments to conversation turns')
        return turns

    def _extract_pii_entities(self, text: str) -> Optional[List[str]]:
        """
        Extract PII entity types from redacted text with tags like <PERSON>, <DATE_TIME>.

        Args:
            text: Text with PII tags

        Returns:
            List of detected PII entity types, or None if none found
        """
        import re

        # Find all PII tags in the text
        pii_tags = re.findall(r'<([A-Z_]+)>', text)

        if not pii_tags:
            return None

        # Return unique tags
        return list(set(pii_tags))


def get_transcription_service() -> Optional[Union[ModalCanaryProvider, AssemblyAIProvider]]:
    """
    Get transcription service instance.
    Prioritizes Modal NVIDIA Canary if enabled, falls back to AssemblyAI.

    Returns:
        ModalCanaryProvider if Modal is enabled and configured,
        AssemblyAIProvider if Modal is disabled but AssemblyAI is configured,
        None if neither provider is configured
    """
    try:
        config = settings.APP_SETTINGS.ai

        # Prioritize Modal if enabled
        if config.modal_enabled and config.modal_app_name:
            logger.info('Using Modal NVIDIA Canary transcription provider')
            return ModalCanaryProvider()

        # Fall back to AssemblyAI
        if config.assemblyai_api_key:
            logger.info('Using AssemblyAI transcription provider')
            return AssemblyAIProvider()

        logger.warning('No transcription provider configured (Modal and AssemblyAI both disabled)')
        return None

    except Exception as e:
        logger.error(f'Failed to create transcription service: {e}')
        return None

