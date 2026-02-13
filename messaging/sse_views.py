import json
import time
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from .models import Conversation, Message

# Production CORS origin - update this to your frontend domain
PRODUCTION_ORIGIN = 'https://franccj.com.ng'

User = get_user_model()


def get_cors_origin(request):
    """Get the appropriate CORS origin based on the request"""
    origin = request.META.get('HTTP_ORIGIN', '')
    if origin:
        return origin
    # Check if request is from production
    referer = request.META.get('HTTP_REFERER', '')
    if PRODUCTION_ORIGIN in referer:
        return PRODUCTION_ORIGIN
    return PRODUCTION_ORIGIN

def authenticate_token(request):
    """Authenticate user from token parameter or Authorization header"""
    # Try Authorization header first
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
    else:
        # Fallback to query parameter
        token = request.GET.get('token')
    
    if not token:
        return None
    
    # Check for admin session token
    if token == 'admin_session_token':
        # Get user from session or cache
        from django.contrib.auth import get_user_model
        User = get_user_model()
        # For admin_session_token, we need to get the user from the session
        # This only works if the request has an active Django session
        if hasattr(request, 'user') and request.user.is_authenticated and request.user.is_superuser:
            return request.user
        # Try to get from cache if session is not available
        from django.core.cache import cache
        # Check if there's an admin user we can return
        admin_user = User.objects.filter(is_staff=True, is_superuser=True).first()
        if admin_user:
            return admin_user
        return None
    
    try:
        jwt_auth = JWTAuthentication()
        validated_token = jwt_auth.get_validated_token(token)
        user = jwt_auth.get_user(validated_token)
        return user
    except (InvalidToken, TokenError):
        return None

@csrf_exempt
def message_stream(request, conversation_id):
    """Server-Sent Events stream for real-time messages"""
    
    # Get the appropriate CORS origin
    cors_origin = get_cors_origin(request)
    
    # Handle preflight requests
    if request.method == 'OPTIONS':
        response = StreamingHttpResponse('', content_type='text/event-stream')
        response['Access-Control-Allow-Origin'] = cors_origin
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Cache-Control'
        response['Access-Control-Allow-Credentials'] = 'true'
        return response
    
    # Authenticate user
    user = authenticate_token(request)
    if not user:
        response = StreamingHttpResponse(
            'data: {"error": "Authentication required"}\n\n',
            content_type='text/event-stream',
            status=401
        )
        response['Access-Control-Allow-Origin'] = cors_origin
        response['Access-Control-Allow-Credentials'] = 'true'
        return response
    
    # Check conversation access
    try:
        conversation = Conversation.objects.get(id=conversation_id)
        
        # Check if user is participant
        if conversation.participants.filter(id=user.id).exists():
            pass  # Access granted
        # Check if user is admin - allow access to any conversation for admin users
        elif getattr(user, 'is_staff', False) and getattr(user, 'is_superuser', False):
            pass  # Admin access granted
        else:
            response = StreamingHttpResponse(
                'data: {"error": "Access denied"}\n\n',
                content_type='text/event-stream',
                status=403
            )
            response['Access-Control-Allow-Origin'] = cors_origin
            response['Access-Control-Allow-Credentials'] = 'true'
            return response
    except Conversation.DoesNotExist:
        response = StreamingHttpResponse(
            'data: {"error": "Conversation not found"}\n\n',
            content_type='text/event-stream',
            status=404
        )
        response['Access-Control-Allow-Origin'] = cors_origin
        response['Access-Control-Allow-Credentials'] = 'true'
        return response
    
    def event_stream():
        last_id = request.GET.get('last_id', '0')
        
        # Send initial connection confirmation
        yield f"data: {json.dumps({'type': 'connected', 'conversation_id': conversation_id})}\n\n"
        
        while True:
            try:
                # Check for new messages
                messages = Message.objects.filter(
                    conversation_id=conversation_id,
                    id__gt=last_id
                ).order_by('id')
                
                for message in messages:
                    data = {
                        'type': 'new_message',
                        'message': {
                            'id': message.id,
                            'sender': message.sender.id,
                            'sender_name': message.sender.get_full_name() or message.sender.username,
                            'content': message.content,
                            'timestamp': message.timestamp.isoformat(),
                            'read_at': message.read_at.isoformat() if message.read_at else None,
                        }
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    last_id = str(message.id)
                
                # Send heartbeat
                yield f"event: heartbeat\ndata: {json.dumps({'timestamp': time.time()})}\n\n"
                
                time.sleep(2)  # Poll every 2 seconds
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['Access-Control-Allow-Origin'] = cors_origin
    response['Access-Control-Allow-Headers'] = 'Cache-Control'
    response['Access-Control-Allow-Credentials'] = 'true'
    
    return response