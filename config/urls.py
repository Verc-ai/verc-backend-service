"""
URL configuration for Verc Backend Service.

This module defines all URL patterns for the Django application, including:
- Admin interface
- API endpoints for authentication, sessions, conversations, tasks
- Health check endpoints
- Root endpoint with basic service information
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from apps.authentication import views as auth_views


def _health_check_response(request):
    """
    Generate standardized health check response.
    
    Args:
        request: Django HTTP request object
        
    Returns:
        dict: Health check response data
    """
    return {
        'status': 'healthy',
        'service': 'verc-backend',
        'version': '1.0.0',
        'test_message': '🧪 TEST: This is a test deployment - workflow verification',
        'request_path': request.path,
        'request_method': request.method,
        'request_meta': {
            k: v for k, v in request.META.items()
            if k.startswith('HTTP_') or k in ['PATH_INFO', 'SCRIPT_NAME', 'REQUEST_URI']
        },
    }


def _get_coming_soon_html():
    """Return the Coming Soon page HTML as a string."""
    # Read from template file if it exists, otherwise return inline HTML
    from pathlib import Path
    template_path = Path(__file__).parent / 'templates' / 'coming_soon.html'
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # Fallback: return a simple Coming Soon page
        return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Verc - Coming Soon</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
      background: #000;
      min-height: 100vh;
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .logo {
      position: absolute;
      top: 2rem;
      left: 2rem;
      font-size: 2.5rem;
      font-weight: 700;
    }
    .coming-soon {
      text-align: center;
    }
    .coming-soon-word {
      font-size: 6rem;
      font-weight: 700;
      line-height: 1.1;
      display: block;
    }
  </style>
</head>
<body>
  <div class="logo">Verc</div>
  <div class="coming-soon">
    <span class="coming-soon-word">Coming</span>
    <span class="coming-soon-word">Soon</span>
  </div>
</body>
</html>"""


def root_view(request):
    """
    Root endpoint that returns Coming Soon page for browsers and JSON for API clients.
    
    Args:
        request: Django HTTP request object
        
    Returns:
        HttpResponse: HTML response for browsers or JSON response for API clients
    """
    if request.headers.get('Accept', '').startswith('text/html'):
        # Return Coming Soon page for browsers
        html = _get_coming_soon_html()
        return HttpResponse(html, content_type='text/html')
    else:
        # Return JSON for API clients
        return JsonResponse({
            'message': 'Verc Backend Service is running',
            'version': '1.0.0',
            'status': 'healthy',
            'endpoints': {
                'health': '/health',
                'auth': '/api/auth/',
                'twilio': '/api/twilio/',
                'conversations': '/api/conversation/',
                'sessions': '/api/sessions/',
            }
        })

@csrf_exempt
@require_http_methods(["OPTIONS"])
def cors_preflight(request):
    """
    Handle CORS preflight OPTIONS requests.
    
    Prevents 301 redirects by handling OPTIONS requests before Django's
    URL routing can redirect them. Sets appropriate CORS headers for
    cross-origin requests.
    
    Args:
        request: Django HTTP request object
        
    Returns:
        HttpResponse: Empty 200 response with CORS headers
    """
    response = HttpResponse(status=200)
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Origin'
    response['Access-Control-Max-Age'] = '86400'
    return response


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Health check endpoints (support both with and without trailing slash for compatibility)
    path('health/', lambda request: JsonResponse(_health_check_response(request)), name='health'),
    path('health', lambda request: JsonResponse(_health_check_response(request)), name='health-no-slash'),
    
    # Authentication endpoints
    # Explicit patterns prevent Django URL resolver redirects
    # Support both with and without trailing slash for Cloud Run compatibility
    path('auth/login', auth_views.LoginView.as_view(), name='auth-login'),
    path('auth/login/', auth_views.LoginView.as_view(), name='auth-login-slash'),
    path('auth/signup', auth_views.SignupView.as_view(), name='auth-signup'),
    path('auth/signup/', auth_views.SignupView.as_view(), name='auth-signup-slash'),
    path('auth/logout/', auth_views.LogoutView.as_view(), name='auth-logout'),
    
    # API endpoints
    # Feature flags - support both with and without trailing slash for frontend compatibility
    path('api/feature-flags/', include('apps.feature_flags.urls')),
    path('api/feature-flags', include('apps.feature_flags.urls')),
    # Sessions - support both with and without trailing slash for frontend compatibility
    path('api/sessions/', include('apps.call_sessions.urls')),
    path('api/sessions', include('apps.call_sessions.urls')),
    # Conversations
    path('api/conversation/', include('apps.conversations.urls')),
    # Tasks - support both with and without trailing slash for Cloud Tasks compatibility
    path('api/tasks/', include('apps.tasks.urls')),
    path('api/tasks', include('apps.tasks.urls')),
    # Twilio webhooks
    path('api/twilio/', include('apps.twilio.urls')),
    # Administration
    path('api/admin/', include('apps.administration.urls')),
    # SOPs endpoint (placeholder for frontend compatibility)
    path('sops', lambda request: JsonResponse({'message': 'SOPs endpoint - to be implemented'}), name='sops'),
    
    # Root endpoint - returns HTML for browsers, JSON for API clients
    path('', root_view, name='root'),
]
