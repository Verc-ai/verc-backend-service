"""
AI Services for generating call summaries and scorecards using OpenAI.
"""
import json
import logging
import os
from typing import Dict, List, Optional, Any
from openai import OpenAI
from django.conf import settings
from apps.core.services.supabase import get_supabase_client

logger = logging.getLogger(__name__)

# Get the directory where this file is located
_AI_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_PROMPTS_DIR = os.path.join(_AI_APP_DIR, 'system_prompts')


class CallSummaryService:
    """Service for generating AI-powered call summaries and scorecards."""
    
    def __init__(self):
        config = settings.APP_SETTINGS.ai
        if not config.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        
        self.client = OpenAI(api_key=config.openai_api_key)
        self.model = 'gpt-4o'
        self.temperature = 0.3
        
        # Load system prompts from files
        self._summary_system_prompt = self._load_prompt('summary_system.txt')
        self._scorecard_system_prompt = self._load_prompt('scorecard_system.txt')
    
    def _load_prompt(self, filename: str) -> str:
        """Load a prompt template from a text file."""
        filepath = os.path.join(_PROMPTS_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.error(f'Prompt file not found: {filepath}')
            raise
        except Exception as e:
            logger.error(f'Error loading prompt file {filepath}: {e}')
            raise
        
    def generate_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Generate AI summary for a call session.
        
        Args:
            session_id: The transcription session ID
            
        Returns:
            Dictionary with summary data
        """
        logger.info(f'Starting summary generation for session {session_id}')
        
        # Fetch transcripts
        transcripts = self._fetch_transcripts(session_id)
        if not transcripts:
            raise ValueError('No transcripts found for session')
        
        # Format transcript
        formatted_transcript = self._format_transcripts(transcripts)
        word_count = len(formatted_transcript.split())
        
        logger.info(f'Transcript has {word_count} words')
        
        # Build prompt
        prompt = self._build_summary_prompt(formatted_transcript, word_count)
        
        # Call OpenAI
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        'role': 'system',
                        'content': self._summary_system_prompt
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                max_tokens=self._calculate_max_tokens(word_count),
                temperature=self.temperature,
                response_format={'type': 'json_object'}
            )
            
            # Parse response
            content = response.choices[0].message.content
            summary_data = json.loads(content)
            
            # Validate
            self._validate_summary_data(summary_data)
            
            logger.info(f'Summary generated successfully for session {session_id}')
            return summary_data
            
        except Exception as e:
            logger.error(f'Failed to generate summary for session {session_id}: {e}', exc_info=True)
            raise
    
    def generate_scorecard(self, session_id: str) -> Dict[str, Any]:
        """
        Generate AI scorecard for a call session.
        
        Args:
            session_id: The transcription session ID
            
        Returns:
            Dictionary with scorecard data
        """
        logger.info(f'Starting scorecard generation for session {session_id}')
        
        # Fetch transcripts
        transcripts = self._fetch_transcripts(session_id)
        if not transcripts:
            raise ValueError('No transcripts found for session')
        
        # Format transcript
        formatted_transcript = self._format_transcripts(transcripts)
        
        # Build prompt
        prompt = self._build_scorecard_prompt(formatted_transcript, transcripts)
        
        # Call OpenAI
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        'role': 'system',
                        'content': self._scorecard_system_prompt
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                max_tokens=self._calculate_scorecard_max_tokens(len(transcripts)),
                temperature=self.temperature,
                response_format={'type': 'json_object'}
            )
            
            # Parse response
            content = response.choices[0].message.content
            raw_scorecard = json.loads(content)
            
            # Transform to match expected structure
            scorecard_data = self._transform_scorecard_data(raw_scorecard)
            
            # Calculate overall weighted score
            scorecard_data['overall_weighted_score'] = self._calculate_overall_weighted_score(scorecard_data)
            
            logger.info(f'Scorecard generated successfully for session {session_id}')
            return scorecard_data
            
        except Exception as e:
            logger.error(f'Failed to generate scorecard for session {session_id}: {e}', exc_info=True)
            raise
    
    def _fetch_transcripts(self, session_id: str) -> List[Dict[str, Any]]:
        """Fetch transcription events from Supabase."""
        supabase = get_supabase_client()
        if not supabase:
            raise ValueError('Supabase client not available')
        
        config = settings.APP_SETTINGS.supabase
        table_name = config.events_table
        
        try:
            # Try ordering by timestamp first, fallback to received_at
            response = supabase.table(table_name)\
                .select('*')\
                .eq('session_id', session_id)\
                .order('received_at', desc=False)\
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            logger.error(f'Failed to fetch transcripts: {e}', exc_info=True)
            return []
    
    def _format_transcripts(self, transcripts: List[Dict[str, Any]]) -> str:
        """Format transcripts for AI processing."""
        formatted = []
        for event in transcripts:
            speaker = event.get('speaker', 'Unknown')
            text = event.get('text', '')
            # Use received_at if available, otherwise timestamp
            timestamp = event.get('received_at') or event.get('timestamp', '')
            
            # Format: [Speaker] (timestamp): text
            formatted.append(f'[{speaker}] ({timestamp}): {text}')
        
        return '\n'.join(formatted)
    
    def _get_summary_length_guidance(self, word_count: int) -> str:
        """Get summary length guidance based on transcript size."""
        if word_count < 200:
            return 'Write 2-3 sharp, direct sentences that capture the essential points'
        elif word_count < 500:
            return 'Write 1 concise paragraph (4-6 short sentences) covering all key points - no fluff'
        elif word_count < 1000:
            return 'Write 2 focused paragraphs covering the conversation flow and important details - be direct and clear'
        elif word_count < 2000:
            return 'Write 3-4 concise paragraphs with full detail on major topics, actions, and outcomes - use short sentences'
        else:
            return 'Write 4-5 thorough but concise paragraphs capturing all aspects of this conversation - be sharp and direct throughout'
    
    def _build_summary_prompt(self, transcript: str, word_count: int) -> str:
        """Build professional summary prompt."""
        length_instruction = self._get_summary_length_guidance(word_count)
        
        # Load prompt template from file
        template = self._load_prompt('summary_user.txt')
        
        # Format the template with dynamic values
        return template.format(
            word_count=word_count,
            length_instruction=length_instruction,
            transcript=transcript
        )
    
    def _build_scorecard_prompt(self, transcript: str, transcripts: List[Dict[str, Any]]) -> str:
        """Build scorecard prompt."""
        # Build transcript list with IDs for sentiment scoring
        transcript_list = []
        for i, t in enumerate(transcripts):
            transcript_id = t.get('id', f'transcript-{i}')
            timestamp = t.get('timestamp', t.get('received_at', ''))
            speaker = t.get('speaker', 'Unknown')
            text = t.get('text', '')
            transcript_list.append(f'[ID: {transcript_id}] [{timestamp}] {speaker}: {text}')
        
        transcript_with_ids = '\n'.join(transcript_list)
        
        # Load prompt template from file
        template = self._load_prompt('scorecard_user.txt')
        
        # Format the template with dynamic values
        return template.format(
            transcript_with_ids=transcript_with_ids
        )
    
    def _calculate_max_tokens(self, word_count: int) -> int:
        """Calculate max tokens based on word count."""
        # Rough estimate: 1 token ≈ 0.75 words
        # Reserve tokens for response (summary is typically 20-30% of input)
        base_tokens = 2000
        if word_count > 2000:
            base_tokens = 4000
        return base_tokens
    
    def _calculate_scorecard_max_tokens(self, transcript_count: int) -> int:
        """Calculate max tokens for scorecard."""
        return 3000
    
    def _validate_summary_data(self, data: Dict[str, Any]) -> None:
        """Validate summary data structure."""
        required_fields = ['title', 'summary', 'direction', 'action_codes', 'result_codes']
        for field in required_fields:
            if field not in data:
                raise ValueError(f'Missing required field: {field}')
    
    def _transform_scorecard_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform OpenAI response to match expected scorecard structure."""
        agent_score = raw_data.get('agent_score', {})
        
        # Transform categories structure
        categories = {}
        
        # Compliance
        compliance = agent_score.get('compliance', {})
        if compliance:
            categories['compliance'] = {
                'score': compliance.get('overall_score', 0.0),
                'feedback': 'Compliance evaluation completed',
                'issues': []
            }
        
        # Servicing
        servicing = agent_score.get('servicing', {})
        if servicing:
            categories['servicing'] = {
                'score': servicing.get('overall_score', 0.0),
                'feedback': 'Servicing evaluation completed',
                'issues': []
            }
        
        # Collections
        collections = agent_score.get('collections', {})
        if collections and collections.get('overall_score') is not None:
            categories['collections'] = {
                'score': collections.get('overall_score', 0.0),
                'feedback': 'Collections evaluation completed',
                'issues': []
            }
        
        # Build final structure
        transformed = {
            'categories': categories,
            'transcript_sentiments': raw_data.get('transcript_sentiments', []),
            'detected_intents': raw_data.get('detected_intents', []),
            'flagged_keywords': raw_data.get('flagged_keywords', []),
            'legal_issues_detected': raw_data.get('legal_issues_detected', False),
            'agent_score': agent_score  # Keep original for detailed view
        }
        
        return transformed
    
    def _calculate_overall_weighted_score(self, scorecard_data: Dict[str, Any]) -> float:
        """Calculate overall weighted score."""
        categories = scorecard_data.get('categories', {})
        
        compliance_score = categories.get('compliance', {}).get('score', 0.0)
        servicing_score = categories.get('servicing', {}).get('score', 0.0)
        collections_score = categories.get('collections', {}).get('score', 0.0) if categories.get('collections') else 0.0
        
        # Check if this is a collections call (has collections activity)
        is_collections_call = collections_score > 0
        
        if is_collections_call:
            # Collections call: 10% compliance + 50% servicing + 40% collections
            weighted_score = (compliance_score * 0.10) + (servicing_score * 0.50) + (collections_score * 0.40)
        else:
            # Non-collections call: 17% compliance + 83% servicing
            weighted_score = (compliance_score * 0.17) + (servicing_score * 0.83)
        
        # Round to 1 decimal place
        return round(weighted_score, 1)

