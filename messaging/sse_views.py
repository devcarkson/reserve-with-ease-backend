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

User = get_user_model()

def authenticate_token(request):
    """Authenticate user from token parameter"""
    token = request.GET.get('token')
    if not token:
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
    
    # Handle preflight requests
    if request.method == 'OPTIONS':
        response = StreamingHttpResponse('', content_type='text/event-stream')
        response['Access-Control-Allow-Origin'] = 'http://localhost:8080'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Cache-Control'
        return response
    
    # Authenticate user
    user = authenticate_token(request)
    if not user:
        response = StreamingHttpResponse(
            'data: {"error": "Authentication required"}\n\n',
            content_type='text/event-stream',
            status=401
        )
        response['Access-Control-Allow-Origin'] = 'http://localhost:8080'
        return response
    
    # Check conversation access
    try:
        conversation = Conversation.objects.get(id=conversation_id)
        if not conversation.participants.filter(id=user.id).exists():
            response = StreamingHttpResponse(
                'data: {"error": "Access denied"}\n\n',
                content_type='text/event-stream',
                status=403
            )
            response['Access-Control-Allow-Origin'] = 'http://localhost:8080'
            return response
    except Conversation.DoesNotExist:
        response = StreamingHttpResponse(
            'data: {"error": "Conversation not found"}\n\n',
            content_type='text/event-stream',
            status=404
        )
        response['Access-Control-Allow-Origin'] = 'http://localhost:8080'
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
    response['Access-Control-Allow-Origin'] = 'http://localhost:8080'
    response['Access-Control-Allow-Headers'] = 'Cache-Control'
    response['Access-Control-Allow-Credentials'] = 'true'
    
    return response