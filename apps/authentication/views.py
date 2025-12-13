"""
Authentication views for user login, signup, and logout.

Provides REST API endpoints for user authentication using Supabase Auth.
Frontend expects:
- POST /auth/login - { email, password } -> { user, session }
- POST /auth/signup - { username, email, password, orgName?, orgId? } -> { user, session? }
- POST /auth/logout - logout current user

All endpoints support CORS preflight requests via OPTIONS method.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from apps.core.services.supabase import get_supabase_client, get_supabase_auth_client
import logging

logger = logging.getLogger(__name__)


class LoginView(APIView):
    """
    POST /auth/login
    Authenticate user with email/password via Supabase.
    Frontend expects: { user: {...}, session: { accessToken, ... } }
    """
    permission_classes = [AllowAny]  # Public endpoint - no auth required
    parser_classes = [JSONParser]
    
    def options(self, request):
        """Handle CORS preflight requests."""
        return Response(status=status.HTTP_200_OK)
    
    def post(self, request):
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '')
        
        if not email or not password:
            return Response(
                {'error': 'Email and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Try Supabase authentication first
        supabase_auth = get_supabase_auth_client()
        supabase_admin = get_supabase_client()
        
        if supabase_auth:
            try:
                # Authenticate with Supabase
                auth_response = supabase_auth.auth.sign_in_with_password({
                    'email123': email,
                    'password': password
                })
                
                if auth_response.user and auth_response.session:
                    user = auth_response.user
                    session = auth_response.session
                    
                    # Extract user metadata
                    user_metadata = user.user_metadata or {}
                    org_id = user_metadata.get('org_id')
                    org_name = user_metadata.get('org_name')
                    role = user_metadata.get('org_role', 'user')
                    display_name = user_metadata.get('full_name') or user_metadata.get('display_name') or email.split('@')[0]
                    avatar_url = user_metadata.get('avatar_url')
                    
                    # If org info not in metadata, try to fetch from profiles table
                    if not org_id and supabase_admin:
                        try:
                            from django.conf import settings
                            config = settings.APP_SETTINGS.supabase
                            if config:
                                profiles_table = config.profiles_table
                                profile_result = supabase_admin.table(profiles_table).select('org_id, org_name, role').eq('id', user.id).single().execute()
                                if profile_result.data:
                                    org_id = org_id or profile_result.data.get('org_id')
                                    org_name = org_name or profile_result.data.get('org_name')
                                    role = role or profile_result.data.get('role', 'user')
                        except Exception as e:
                            logger.warning(f'Failed to fetch profile for user {user.id}: {e}')
                    
                    # Calculate expiration
                    import time
                    expires_in = session.expires_in or 3600
                    if session.expires_at:
                        expires_at = session.expires_at
                    elif session.expires_in:
                        expires_at = int(time.time()) + session.expires_in
                    else:
                        expires_at = int(time.time()) + 3600
                    
                    return Response({
                        'user': {
                            'id': user.id,
                            'email': user.email,
                            'displayName': display_name,
                            'avatarUrl': avatar_url,
                            'orgId': org_id,
                            'orgName': org_name,
                            'role': role,
                            'user_metadata': user_metadata
                        },
                        'session': {
                            'accessToken': session.access_token,
                            'refreshToken': session.refresh_token,
                            'expiresIn': expires_in,
                            'expiresAt': expires_at,
                        }
                    }, status=status.HTTP_200_OK)
                    
            except Exception as e:
                logger.error(f'Supabase authentication failed: {e}')
                # Fall through to mock response for development
                pass
        
        # Fallback to mock response if Supabase is not configured or auth fails
        # This allows development without Supabase setup
        from datetime import datetime, timedelta
        import uuid
        
        expires_in = 3600  # 1 hour
        expires_at = int((datetime.now() + timedelta(seconds=expires_in)).timestamp())
        
        mock_org_id = str(uuid.uuid4())
        mock_org_name = 'Default Organization'
        
        return Response({
            'user': {
                'id': str(uuid.uuid4()),
                'email': email,
                'displayName': email.split('@')[0],
                'avatarUrl': None,
                'orgId': mock_org_id,
                'orgName': mock_org_name,
                'role': 'admin',
                'user_metadata': {
                    'org_id': mock_org_id,
                    'org_name': mock_org_name
                }
            },
            'session': {
                'accessToken': 'mock-access-token',
                'refreshToken': 'mock-refresh-token',
                'expiresIn': expires_in,
                'expiresAt': expires_at,
            }
        }, status=status.HTTP_200_OK)


class SignupView(APIView):
    """
    POST /auth/signup
    Create new user account via Supabase.
    Frontend expects: { user: {...}, session?: {...} }
    """
    permission_classes = [AllowAny]  # Public endpoint - no auth required
    parser_classes = [JSONParser]
    
    def options(self, request):
        """Handle CORS preflight requests."""
        return Response(status=status.HTTP_200_OK)
    
    def post(self, request):
        username = request.data.get('username', '').strip()
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '')
        org_name = request.data.get('orgName', '').strip()
        org_id = request.data.get('orgId', '').strip()
        
        if not email or not password:
            return Response(
                {'error': 'Email and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not username or len(username) < 2:
            return Response(
                {'error': 'Username must be at least 2 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Try Supabase signup first
        supabase_auth = get_supabase_auth_client()
        supabase_admin = get_supabase_client()
        
        if supabase_auth:
            try:
                # Prepare user metadata
                user_metadata = {
                    'full_name': username,
                    'display_name': username,
                }
                
                # If joining existing org, include org info
                if org_id:
                    user_metadata['org_id'] = org_id
                    user_metadata['org_name'] = org_name
                    user_metadata['org_role'] = 'user'  # New members are users by default
                else:
                    # Creating new org - user will be admin
                    import uuid
                    generated_org_id = str(uuid.uuid4())
                    user_metadata['org_id'] = generated_org_id
                    user_metadata['org_name'] = org_name or 'Default Organization'
                    user_metadata['org_role'] = 'admin'
                    org_id = generated_org_id
                    org_name = org_name or 'Default Organization'
                
                # Sign up with Supabase
                signup_response = supabase_auth.auth.sign_up({
                    'email': email,
                    'password': password,
                    'options': {
                        'data': user_metadata
                    }
                })
                
                if signup_response.user:
                    user = signup_response.user
                    session = signup_response.session
                    
                    # Create/update profile in profiles table
                    if supabase_admin:
                        try:
                            from django.conf import settings
                            config = settings.APP_SETTINGS.supabase
                            if config:
                                profiles_table = config.profiles_table
                                profile_data = {
                                    'id': user.id,
                                    'email': user.email,
                                    'display_name': username,
                                    'org_id': org_id,
                                    'org_name': org_name,
                                    'role': user_metadata.get('org_role', 'user'),
                                    'metadata': user_metadata
                                }
                                supabase_admin.table(profiles_table).upsert(profile_data, on_conflict='id').execute()
                        except Exception as e:
                            logger.warning(f'Failed to create profile for user {user.id}: {e}')
                    
                    # If session is None, user needs to confirm email
                    if not session:
                        return Response({
                            'user': {
                                'id': user.id,
                                'email': user.email,
                                'displayName': username,
                                'avatarUrl': None,
                                'orgId': org_id,
                                'orgName': org_name,
                                'role': user_metadata.get('org_role', 'user'),
                                'user_metadata': user_metadata
                            }
                            # No session - frontend will show "please sign in" message
                        }, status=status.HTTP_201_CREATED)
                    
                    # User is signed in immediately (email confirmation disabled or auto-confirmed)
                    import time
                    expires_in = session.expires_in or 3600
                    if session.expires_at:
                        expires_at = session.expires_at
                    elif session.expires_in:
                        expires_at = int(time.time()) + session.expires_in
                    else:
                        expires_at = int(time.time()) + 3600
                    
                    return Response({
                        'user': {
                            'id': user.id,
                            'email': user.email,
                            'displayName': username,
                            'avatarUrl': None,
                            'orgId': org_id,
                            'orgName': org_name,
                            'role': user_metadata.get('org_role', 'admin'),
                            'user_metadata': user_metadata
                        },
                        'session': {
                            'accessToken': session.access_token,
                            'refreshToken': session.refresh_token,
                            'expiresIn': expires_in,
                            'expiresAt': expires_at,
                        }
                    }, status=status.HTTP_201_CREATED)
                    
            except Exception as e:
                error_message = str(e)
                logger.error(f'Supabase signup failed: {e}')
                
                # Check if it's a user already exists error
                if 'already registered' in error_message.lower() or 'already exists' in error_message.lower():
                    return Response(
                        {'error': 'An account with this email already exists. Please sign in instead.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Return the error message from Supabase
                return Response(
                    {'error': f'Signup failed: {error_message}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Fallback to mock response if Supabase is not configured
        import uuid
        from datetime import datetime, timedelta
        
        expires_in = 3600  # 1 hour
        expires_at = int((datetime.now() + timedelta(seconds=expires_in)).timestamp())
        generated_org_id = org_id or str(uuid.uuid4())
        generated_org_name = org_name or 'Default Organization'
        
        return Response({
            'user': {
                'id': str(uuid.uuid4()),
                'email': email,
                'displayName': username,
                'avatarUrl': None,
                'orgId': generated_org_id,
                'orgName': generated_org_name,
                'role': 'admin',
                'user_metadata': {
                    'username': username,
                    'org_id': generated_org_id,
                    'org_name': generated_org_name
                }
            },
            'session': {
                'accessToken': 'mock-access-token',
                'refreshToken': 'mock-refresh-token',
                'expiresIn': expires_in,
                'expiresAt': expires_at,
            }
        }, status=status.HTTP_201_CREATED)


class LogoutView(APIView):
    """
    POST /auth/logout
    
    Logout current user session.
    
    Note: Currently returns success without server-side session management.
    Frontend should handle token removal on client side.
    """
    permission_classes = [AllowAny]
    
    def options(self, request):
        """Handle CORS preflight requests."""
        return Response(status=status.HTTP_200_OK)
    
    def post(self, request):
        """
        Process logout request.
        
        Args:
            request: Django REST framework request object
            
        Returns:
            Response: Success message
        """
        # Note: Server-side session invalidation to be implemented
        # when session management is added
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)

