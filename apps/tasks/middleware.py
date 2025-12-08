"""
Cloud Tasks authentication middleware for Django.
Validates that incoming requests are from Google Cloud Tasks.
"""
from django.http import JsonResponse
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class CloudTasksAuthMiddleware:
    """
    Middleware to validate Cloud Tasks requests.
    
    Checks for:
    - X-CloudTasks-TaskName header (required)
    - X-CloudTasks-QueueName header (required)
    - Queue name matches configuration
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Only validate Cloud Tasks endpoints
        if request.path.startswith('/api/tasks/'):
            task_name = request.headers.get('X-CloudTasks-TaskName')
            queue_name = request.headers.get('X-CloudTasks-QueueName')
            
            # Validate required headers exist
            if not task_name:
                logger.warning(
                    f'Missing X-CloudTasks-TaskName header for {request.path}',
                    extra={'headers': dict(request.headers)}
                )
                return JsonResponse(
                    {'error': 'Unauthorized: Missing task name header'},
                    status=401
                )
            
            if not queue_name:
                logger.warning(
                    f'Missing X-CloudTasks-QueueName header for {request.path}',
                    extra={'headers': dict(request.headers)}
                )
                return JsonResponse(
                    {'error': 'Unauthorized: Missing queue name header'},
                    status=401
                )
            
            # Validate queue name matches configuration
            config = settings.APP_SETTINGS.cloud_tasks
            if queue_name != config.queue_name:
                logger.warning(
                    f'Queue name mismatch for {request.path}: expected {config.queue_name}, got {queue_name}',
                    extra={'task_name': task_name, 'queue_name': queue_name}
                )
                return JsonResponse(
                    {'error': 'Unauthorized: Invalid queue name'},
                    status=401
                )
            
            logger.debug(
                f'Cloud Tasks request validated: taskName={task_name}, queueName={queue_name}, path={request.path}'
            )
        
        response = self.get_response(request)
        return response

