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
        'request_path': request.path,
        'request_method': request.method,
        'request_meta': {
            k: v for k, v in request.META.items()
            if k.startswith('HTTP_') or k in ['PATH_INFO', 'SCRIPT_NAME', 'REQUEST_URI']
        },
    }


def root_view(request):
    """
    Root endpoint that returns HTML for browsers and JSON for API clients.
    
    Args:
        request: Django HTTP request object
        
    Returns:
        HttpResponse: HTML response for browsers or JSON response for API clients
    """
    if request.headers.get('Accept', '').startswith('text/html'):
        # Return HTML for browsers
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verc Backend Service</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            max-width: 600px;
            width: 100%;
        }
        h1 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .status {
            display: inline-block;
            padding: 6px 12px;
            background: #10b981;
            color: white;
            border-radius: 20px;
            font-size: 0.9em;
            margin-bottom: 30px;
        }
        .endpoints {
            margin-top: 30px;
        }
        .endpoints h2 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        .endpoint {
            background: #f7fafc;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .endpoint code {
            background: #edf2f7;
            padding: 4px 8px;
            border-radius: 4px;
            font-family: 'Monaco', 'Courier New', monospace;
            color: #667eea;
        }
        .method {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
            margin-right: 8px;
        }
        .get { background: #10b981; color: white; }
        .post { background: #3b82f6; color: white; }
        a {
            color: #667eea;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
            color: #718096;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Verc Backend Service</h1>
        <span class="status">Running</span>
        <p style="color: #718096; margin-top: 15px; line-height: 1.6;">
            Django backend service is running successfully. Use the endpoints below to interact with the API.
        </p>
        
        <div class="endpoints">
            <h2>Available Endpoints</h2>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <a href="/health"><code>/health</code></a>
                <p style="margin-top: 8px; color: #718096; font-size: 0.9em;">Health check endpoint</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/twilio/status</code>
                <p style="margin-top: 8px; color: #718096; font-size: 0.9em;">Twilio service status</p>
            </div>
            
            <div class="endpoint">
                <span class="method post">POST</span>
                <code>/auth/login</code>
                <p style="margin-top: 8px; color: #718096; font-size: 0.9em;">User authentication</p>
            </div>
            
            <div class="endpoint">
                <span class="method post">POST</span>
                <code>/auth/signup</code>
                <p style="margin-top: 8px; color: #718096; font-size: 0.9em;">User registration</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/sessions</code>
                <p style="margin-top: 8px; color: #718096; font-size: 0.9em;">Call sessions</p>
            </div>
            
            <div class="endpoint">
                <span class="method post">POST</span>
                <code>/api/conversation</code>
                <p style="margin-top: 8px; color: #718096; font-size: 0.9em;">Conversation management</p>
            </div>
        </div>
        
        <div class="footer">
            <p><strong>Version:</strong> 1.0.0</p>
            <p><strong>Framework:</strong> Django 5.0 + Django REST Framework</p>
            <p><strong>Python:</strong> 3.12+</p>
        </div>
    </div>
</body>
</html>
        """
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
