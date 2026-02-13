"""
JWT-based authentication endpoint for frontend access when logged into Django admin.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework_simplejwt.tokens import RefreshToken
import json

User = get_user_model()


def get_tokens_for_user(user):
    """Generate JWT tokens for a user"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


@require_http_methods(["GET"])
def validate_admin_token(request):
    """
    Validate admin token and return JWT tokens for frontend.
    Frontend calls this with ?token=xxx to authenticate.
    """
    token = request.GET.get('token')
    if not token:
        return JsonResponse({'valid': False, 'message': 'No token provided'}, status=400)
    
    user_id = cache.get(f'admin_session_token_{token}')
    if not user_id:
        return JsonResponse({'valid': False, 'message': 'Invalid or expired token'}, status=401)
    
    try:
        user = User.objects.get(id=user_id)
        if not user.is_superuser:
            return JsonResponse({'valid': False, 'message': 'User is not a superuser'}, status=403)
        
        # Delete token after use (one-time use)
        cache.delete(f'admin_session_token_{token}')
        
        # Generate JWT tokens for the frontend
        tokens = get_tokens_for_user(user)
        
        return JsonResponse({
            'valid': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_superuser': user.is_superuser,
                'is_staff': user.is_staff,
            },
            'tokens': tokens
        })
    except User.DoesNotExist:
        return JsonResponse({'valid': False, 'message': 'User not found'}, status=404)


@require_http_methods(["GET"])
def admin_session_auth(request):
    """
    Check if user is logged into Django admin and return their info.
    Frontend can call this endpoint to check admin session status.
    """
    if request.user.is_authenticated and request.user.is_superuser:
        user = request.user
        return JsonResponse({
            'authenticated': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_superuser': user.is_superuser,
                'is_staff': user.is_staff,
            }
        })
    else:
        return JsonResponse({
            'authenticated': False,
            'message': 'Not logged into Django admin'
        }, status=401)


@require_http_methods(["POST"])
def admin_session_login(request):
    """
    Login to backend using Django admin credentials and return JWT tokens.
    """
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        from django.contrib.auth import authenticate
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_superuser:
            # Generate JWT tokens
            tokens = get_tokens_for_user(user)
            return JsonResponse({
                'success': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_superuser': user.is_superuser,
                    'is_staff': user.is_staff,
                },
                'tokens': tokens
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid credentials or not a superuser'
            }, status=401)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
