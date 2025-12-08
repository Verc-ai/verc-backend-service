"""
Transcription service using AssemblyAI for audio transcription with speaker diarization.
"""
import logging
from typing import List, Dict, Any, Optional
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
            
            return turns
            
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


def get_transcription_service() -> Optional[AssemblyAIProvider]:
    """
    Get transcription service instance.
    
    Returns:
        AssemblyAIProvider instance if configured, None otherwise
    """
    try:
        config = settings.APP_SETTINGS.ai
        if not config.assemblyai_api_key:
            logger.warning('AssemblyAI API key not configured')
            return None
        
        return AssemblyAIProvider()
    except Exception as e:
        logger.error(f'Failed to create transcription service: {e}')
        return None

