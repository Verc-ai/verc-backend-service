"""
Google Cloud Tasks service for queuing async transcription and AI analysis tasks.
"""
try:
    from google.cloud import tasks_v2
    CLOUD_TASKS_AVAILABLE = True
except ImportError:
    CLOUD_TASKS_AVAILABLE = False
    tasks_v2 = None

from django.conf import settings
import logging
import json

logger = logging.getLogger(__name__)

_cloud_tasks_client = None


def get_cloud_tasks_client():
    """
    Get or create Cloud Tasks client singleton.
    Returns None if Cloud Tasks is not configured or enabled.
    """
    global _cloud_tasks_client
    
    if not CLOUD_TASKS_AVAILABLE:
        logger.warning('google-cloud-tasks package not available')
        return None
    
    config = settings.APP_SETTINGS.cloud_tasks
    
    if not config.enabled:
        logger.debug('Cloud Tasks is disabled in configuration')
        return None
    
    if not config.project_id or not config.region or not config.queue_name:
        logger.warning(
            f'Cloud Tasks enabled but configuration incomplete: '
            f'project_id={bool(config.project_id)}, region={bool(config.region)}, '
            f'queue_name={bool(config.queue_name)}'
        )
        return None
    
    if _cloud_tasks_client is not None:
        return _cloud_tasks_client
    
    try:
        _cloud_tasks_client = tasks_v2.CloudTasksClient()
        logger.info(f'Cloud Tasks client initialized for queue: {config.queue_name}')
        return _cloud_tasks_client
    except Exception as e:
        logger.error(f'Failed to create Cloud Tasks client: {e}')
        return None


def enqueue_transcription_task(session_id: str, storage_path: str, service_url: str) -> bool:
    """
    Enqueue a transcription task to Cloud Tasks.
    
    Args:
        session_id: The transcription session ID
        storage_path: Path to the audio file in storage
        service_url: Base URL of the Cloud Run service (e.g., https://your-service.run.app)
    
    Returns:
        True if task was enqueued successfully, False otherwise
    """
    client = get_cloud_tasks_client()
    if not client:
        logger.warning('Cloud Tasks client not available, skipping task enqueue')
        return False
    
    config = settings.APP_SETTINGS.cloud_tasks
    
    try:
        # Construct the fully qualified queue name
        queue_path = client.queue_path(
            config.project_id,
            config.region,
            config.queue_name
        )
        
        import sys
        print(f'[CLOUD_TASKS] Queue path: {queue_path}, Project: {config.project_id}, Region: {config.region}, Queue: {config.queue_name}', file=sys.stderr, flush=True)
        logger.info(
            f'Queue path: {queue_path}, '
            f'Project: {config.project_id}, Region: {config.region}, Queue: {config.queue_name}'
        )
        
        # Construct the task endpoint URL
        endpoint = f'{service_url}/api/tasks/transcribe-audio'
        
        # Create task payload
        payload = {
            'sessionId': session_id,
            'storagePath': storage_path
        }
        
        payload_json = json.dumps(payload)
        payload_bytes = payload_json.encode('utf-8')
        
        import sys
        print(f'[CLOUD_TASKS] Creating task: endpoint={endpoint}, payload={payload_json}, service_account={config.service_account_email}', file=sys.stderr, flush=True)
        logger.info(
            f'Creating task: endpoint={endpoint}, payload={payload_json}, '
            f'service_account={config.service_account_email}'
        )
        
        # Create the task
        task = {
            'http_request': {
                'http_method': tasks_v2.HttpMethod.POST,
                'url': endpoint,
                'headers': {
                    'Content-Type': 'application/json',
                },
                'body': payload_bytes,
            }
        }
        
        # Set dispatch deadline to 30 minutes (1800 seconds) for transcription
        # Transcription can take a long time, so we need a generous timeout
        # Maximum is 30 minutes for HTTP tasks
        from datetime import timedelta
        task['dispatch_deadline'] = timedelta(seconds=1800)  # 30 minutes
        
        # Add OIDC token for authentication if service account is configured
        if config.service_account_email:
            task['http_request']['oidc_token'] = {
                'service_account_email': config.service_account_email,
            }
            logger.info(f'Using OIDC token authentication with service account: {config.service_account_email}')
        else:
            logger.warning('No service account email configured - task may fail authentication')
        
        # Create the task request
        request = {
            'parent': queue_path,
            'task': task,
        }
        
        import sys
        print(f'[CLOUD_TASKS] Calling client.create_task with parent: {queue_path}', file=sys.stderr, flush=True)
        logger.info(f'Calling client.create_task with parent: {queue_path}')
        
        # Enqueue the task
        response = client.create_task(request=request)
        
        print(f'[CLOUD_TASKS] ✅ Task enqueued! Task name: {response.name}, Session: {session_id}', file=sys.stderr, flush=True)
        logger.info(
            f'✅ Transcription task enqueued successfully! '
            f'Task name: {response.name}, Session: {session_id}, '
            f'Queue: {config.queue_name}, URL: {endpoint}'
        )
        return True
        
    except Exception as e:
        import sys
        import traceback
        print(f'[CLOUD_TASKS] ❌ Failed to enqueue task: {e}', file=sys.stderr, flush=True)
        print(f'[CLOUD_TASKS] Traceback: {traceback.format_exc()}', file=sys.stderr, flush=True)
        logger.error(
            f'❌ Failed to enqueue transcription task for session {session_id}: {e}',
            exc_info=True
        )
        logger.error(f'Full traceback: {traceback.format_exc()}')
        return False


def enqueue_ai_analysis_task(session_id: str, service_url: str) -> bool:
    """
    Enqueue an AI analysis task (summary + scorecard) to Cloud Tasks.
    
    Args:
        session_id: The transcription session ID
        service_url: Base URL of the Cloud Run service
    
    Returns:
        True if task was enqueued successfully, False otherwise
    """
    client = get_cloud_tasks_client()
    if not client:
        logger.warning('Cloud Tasks client not available, skipping AI analysis task enqueue')
        return False
    
    config = settings.APP_SETTINGS.cloud_tasks
    
    try:
        # Construct the fully qualified queue name
        queue_path = client.queue_path(
            config.project_id,
            config.region,
            config.queue_name
        )
        
        # Construct the task endpoint URL
        endpoint = f'{service_url}/api/tasks/generate-ai-analysis'
        
        # Create task payload
        payload = {
            'sessionId': session_id,
        }
        
        # Create the task
        task = {
            'http_request': {
                'http_method': tasks_v2.HttpMethod.POST,
                'url': endpoint,
                'headers': {
                    'Content-Type': 'application/json',
                },
                'body': json.dumps(payload).encode(),
            }
        }
        
        # Set dispatch deadline to 30 minutes (1800 seconds) for AI analysis
        from datetime import timedelta
        task['dispatch_deadline'] = timedelta(seconds=1800)  # 30 minutes
        
        # Add OIDC token for authentication if service account is configured
        if config.service_account_email:
            task['http_request']['oidc_token'] = {
                'service_account_email': config.service_account_email,
            }
        
        # Create the task request
        request = {
            'parent': queue_path,
            'task': task,
        }
        
        import sys
        print(f'[CLOUD_TASKS] Enqueueing AI analysis task for session {session_id}, endpoint={endpoint}', file=sys.stderr, flush=True)
        
        # Enqueue the task
        response = client.create_task(request=request)
        
        print(f'[CLOUD_TASKS] ✅ AI analysis task enqueued! Task name: {response.name}, Session: {session_id}', file=sys.stderr, flush=True)
        logger.info(
            f'AI analysis task enqueued: {response.name} for session {session_id}'
        )
        return True
        
    except Exception as e:
        logger.error(f'Failed to enqueue AI analysis task: {e}', exc_info=True)
        return False

