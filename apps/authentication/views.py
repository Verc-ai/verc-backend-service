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
                    'email': email,
                    'password': password
                })
                
                if auth_response.user and auth_response.session:
                    user = auth_response.user
                    session = auth_response.session

                    # Check approval status from profiles table
                    if supabase_admin:
                        try:
                            from django.conf import settings
                            config = settings.APP_SETTINGS.supabase
                            if config:
                                profiles_table = config.profiles_table
                                profile_result = supabase_admin.table(profiles_table).select('approved, org_id, org_name, role, display_name, avatar_url').eq('id', user.id).single().execute()

                                if profile_result.data:
                                    profile = profile_result.data
                                    approved = profile.get('approved', False)

                                    # Check if user is approved
                                    if not approved:
                                        logger.warning(f'Login attempt by unapproved user {user.email}')
                                        return Response(
                                            {'error': 'Your account is pending approval. Please contact an administrator.'},
                                            status=status.HTTP_403_FORBIDDEN
                                        )

                                    # Check if org is assigned
                                    org_id = profile.get('org_id')
                                    if not org_id:
                                        logger.warning(f'Login attempt by user {user.email} without org assignment')
                                        return Response(
                                            {'error': 'Your account has not been configured yet. Please contact an administrator.'},
                                            status=status.HTTP_403_FORBIDDEN
                                        )

                                    # User is approved and has org - proceed with login
                                    org_name = profile.get('org_name')
                                    role = profile.get('role', 'user')
                                    display_name = profile.get('display_name') or email.split('@')[0]
                                    avatar_url = profile.get('avatar_url')

                                else:
                                    # Profile not found - shouldn't happen but handle it
                                    logger.error(f'Profile not found for user {user.id}')
                                    return Response(
                                        {'error': 'Account profile not found. Please contact an administrator.'},
                                        status=status.HTTP_403_FORBIDDEN
                                    )
                        except Exception as e:
                            logger.error(f'Failed to fetch profile for user {user.id}: {e}')
                            return Response(
                                {'error': 'Failed to verify account status. Please try again.'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR
                            )
                    else:
                        # Supabase admin client not available
                        logger.error('Supabase admin client not available for profile check')
                        return Response(
                            {'error': 'Authentication service error. Please try again.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )

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
                            'role': role
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
                return Response(
                    {'error': 'Invalid email or password'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        # Supabase client not configured
        logger.error('Supabase authentication is not configured')
        return Response(
            {'error': 'Authentication service is unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


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

        # Try Supabase signup
        supabase_auth = get_supabase_auth_client()
        supabase_admin = get_supabase_client()

        if supabase_auth:
            try:
                # Simplified user metadata - no org info
                user_metadata = {
                    'full_name': username,
                    'display_name': username,
                }

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

                    # Create profile in profiles table with approved=false
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
                                    'org_id': None,  # Admin will assign
                                    'org_name': None,  # Admin will assign
                                    'role': None,  # Admin will assign
                                    'approved': False,  # Requires admin approval
                                    'metadata': user_metadata
                                }
                                supabase_admin.table(profiles_table).upsert(profile_data, on_conflict='id').execute()
                                logger.info(f'Created unapproved profile for user {user.email}')
                        except Exception as e:
                            logger.warning(f'Failed to create profile for user {user.id}: {e}')

                    # Return success without session - user must wait for approval
                    return Response({
                        'message': 'Account created successfully. Your account will be activated once approved by an administrator.',
                        'user': {
                            'id': user.id,
                            'email': user.email,
                            'displayName': username
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

        # Supabase client not configured
        logger.error('Supabase authentication is not configured')
        return Response(
            {'error': 'Authentication service is unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


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

