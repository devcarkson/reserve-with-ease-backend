from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.response import Response
from rest_framework.renderers import BaseRenderer


class EventStreamRenderer(BaseRenderer):
    """Minimal renderer for Server-Sent Events"""
    media_type = 'text/event-stream'
    format = 'event-stream'

    def render(self, data, media_type=None, renderer_context=None):
        # DRF expects a bytes/str return value from renderers; StreamingHttpResponse will bypass this,
        # but providing a renderer that declares 'text/event-stream' avoids 406 responses from content negotiation.
        return data
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.http import StreamingHttpResponse
import json
from .models import Conversation, Message, MessageAttachment, MessageReaction, ConversationSettings, MessageReport
from .serializers import (
    ConversationSerializer, MessageSerializer, MessageCreateSerializer,
    MessageAttachmentSerializer, MessageReactionSerializer, ConversationSettingsSerializer,
    MessageReportSerializer
)

User = get_user_model()


class IsConversationParticipant(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user in obj.participants.all()


class ConversationListView(generics.ListAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering = ['-updated_at']

    def get_queryset(self):
        user = self.request.user
        print(f"DEBUG: ConversationListView - User {user.id} ({user.username}) is_staff: {getattr(user, 'is_staff', False)} is_superuser: {getattr(user, 'is_superuser', False)}")
        
        qs = Conversation.objects.filter(participants=user).distinct()
        print(f"DEBUG: Base queryset count: {qs.count()}")
        
        # Debug: Print all conversations for this user
        for conv in qs:
            participants = [f"{p.username}({p.id})" for p in conv.participants.all()]
            print(f"DEBUG: Conversation {conv.id} participants: {participants}")
        
        participant_type = self.request.query_params.get('participant_type')
        print(f"DEBUG: participant_type filter: {participant_type}")
        
        # For admin users, show all conversations where admin is participant
        if getattr(user, 'is_staff', False) and getattr(user, 'is_superuser', False):
            print(f"DEBUG: Admin user detected, returning all conversations where admin is participant")
            return qs
        
        # Filter for owners to show only conversations with guests when requested
        if participant_type == 'guest' and (getattr(user, 'role', None) == 'owner' or getattr(user, 'role', None) == 'single_owner'):
            # Get conversations where at least one other participant is a guest (role='user')
            guest_conversations = []
            for conv in qs:
                other_participants = conv.participants.exclude(id=user.id)
                if other_participants.filter(role='user').exists():
                    guest_conversations.append(conv.id)
            qs = qs.filter(id__in=guest_conversations)
            print(f"DEBUG: After guest filter count: {qs.count()}")

        # Optional: filter conversations related to a specific property via reservations
        prop_filter = self.request.query_params.get('property_filter')
        if prop_filter:
            try:
                from reservations.models import Reservation
                # Find reservations for this property
                res_qs = Reservation.objects.filter(
                    Q(property_obj__id=prop_filter) | Q(property=prop_filter)
                )
                conv_qs = Conversation.objects.none()
                for res in res_qs:
                    owner = getattr(res.property_obj, 'owner', None) if getattr(res, 'property_obj', None) else None
                    guest = getattr(res, 'user', None)
                    if owner and guest:
                        conv_qs = conv_qs | Conversation.objects.filter(participants=owner).filter(participants=guest)
                return conv_qs.distinct()
            except Exception:
                # Fall back to original qs on error
                return qs

        return qs


class ConversationDetailView(generics.RetrieveAPIView):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated, IsConversationParticipant]

    def get_object(self):
        conversation = super().get_object()
        # Mark messages as read for this user
        Message.objects.filter(
            conversation=conversation,
            receiver=self.request.user,
            read_at__isnull=True
        ).update(read_at=timezone.now())
        
        # Update unread count
        Message.objects.filter(
            conversation=conversation,
            receiver=self.request.user,
            read_at__isnull=True
        ).count()
        conversation.set_unread_count(self.request.user, 0)
        conversation.save()
        
        return conversation


class MessageListView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering = ['timestamp']

    def get_queryset(self):
        user = self.request.user
        conversation_id = self.kwargs['conversation_id']
        print(f"DEBUG: MessageListView - User {user.id} ({user.username}) accessing conversation {conversation_id}")
        
        # Ensure the requester is a participant OR is admin accessing admin support conversation
        try:
            conv = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Message.objects.none()
        
        # Check if user is participant
        if conv.participants.filter(id=user.id).exists():
            print(f"DEBUG: User is participant in conversation")
            return Message.objects.filter(
                conversation_id=conversation_id,
                deleted_at__isnull=True
            )
        
        # Check if user is admin and this is an admin support conversation
        admin_user = User.objects.filter(is_staff=True, is_superuser=True).first()
        if admin_user and conv.participants.filter(id=admin_user.id).exists():
            print(f"DEBUG: Admin support conversation access granted for user {user.id}")
            return Message.objects.filter(
                conversation_id=conversation_id,
                deleted_at__isnull=True
            )
        
        print(f"DEBUG: Access denied for user {user.id} - not participant and not admin support conversation")
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Not a participant of this conversation")


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def debug_create_test_conversation(request):
    """Debug endpoint to create test conversation"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Find a guest user (role='user') and current user should be owner
    guest = User.objects.filter(role='user').first()
    owner = request.user
    
    if not guest:
        return Response({'error': 'No guest users found'}, status=400)
    
    if getattr(owner, 'role', None) != 'owner':
        return Response({'error': 'Current user is not an owner'}, status=400)
    
    # Create conversation
    conversation = Conversation.objects.create()
    conversation.participants.add(owner, guest)
    
    # Create initial message
    message = Message.objects.create(
        conversation=conversation,
        sender=guest,
        receiver=owner,
        content=f"Hello! I'm interested in your property. This is a test message from {guest.username}.",
        message_type='text'
    )
    
    conversation.last_message = message
    conversation.save()
    
    # Set unread count for owner
    conversation.set_unread_count(owner, 1)
    
    return Response({
        'message': 'Test conversation created',
        'conversation_id': conversation.id,
        'participants': [owner.username, guest.username]
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_conversation_view(request):
    """Create a new conversation"""
    try:
        receiver_id = request.data.get('receiver_id')
        initial_message = request.data.get('message', '')
        
        if not receiver_id:
            return Response({'error': 'Receiver ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            receiver = User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            return Response({'error': 'Receiver not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if receiver == request.user:
            return Response({'error': 'Cannot create conversation with yourself'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if conversation already exists
        existing_conversation = Conversation.objects.filter(
            participants=request.user
        ).filter(participants=receiver).first()

        if existing_conversation:
            serializer = ConversationSerializer(existing_conversation, context={'request': request})
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )

        # Create new conversation
        conversation = Conversation.objects.create()
        conversation.participants.add(request.user, receiver)

        # Send initial message if provided
        if initial_message:
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                receiver=receiver,
                content=initial_message,
                message_type=request.data.get('message_type', 'text')
            )

            # Update conversation
            conversation.last_message = message
            conversation.save()

            # Update unread count for receiver
            conversation.set_unread_count(receiver, 1)
            conversation.save()

            return Response(
                MessageSerializer(message, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )

        serializer = ConversationSerializer(conversation, context={'request': request})
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        import traceback
        print(f"Error in create_conversation_view: {e}")
        traceback.print_exc()
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_messages_read_view(request, conversation_id):
    """Mark all messages in conversation as read"""
    try:
        conversation = Conversation.objects.get(id=conversation_id)
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user is participant OR admin accessing admin support conversation
    is_participant = conversation.participants.filter(id=request.user.id).exists()
    admin_user = User.objects.filter(is_staff=True, is_superuser=True).first()
    is_admin_conversation = admin_user and conversation.participants.filter(id=admin_user.id).exists()
    
    if not (is_participant or is_admin_conversation):
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    # Mark all unread messages as read
    Message.objects.filter(
        conversation=conversation,
        receiver=request.user,
        read_at__isnull=True
    ).update(read_at=timezone.now())
    
    # Update unread count
    conversation.set_unread_count(request.user, 0)
    conversation.save()
    
    return Response({'message': 'Messages marked as read'})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_message_attachment_view(request, conversation_id):
    """Upload attachment for a message"""
    try:
        conversation = Conversation.objects.get(id=conversation_id)
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)
    # Ensure participant
    if not conversation.participants.filter(id=request.user.id).exists():
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    attachment = request.FILES.get('file')
    if not attachment:
        return Response({'error': 'File is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    message_content = request.data.get('content', '')
    other_participant = conversation.participants.exclude(id=request.user.id).first()
    
    # Create message with attachment
    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        receiver=other_participant,
        content=message_content,
        message_type='file',
        attachment_name=attachment.name,
        attachment_size=attachment.size
    )
    
    # Create attachment record
    attachment_record = MessageAttachment.objects.create(
        message=message,
        file=attachment,
        filename=attachment.name,
        file_size=attachment.size,
        file_type=attachment.content_type
    )
    if hasattr(attachment_record.file, 'url'):
        message.attachment_url = attachment_record.file.url
        message.save(update_fields=['attachment_url'])
    
    # Update conversation
    conversation.last_message = message
    conversation.save()
    
    # Update unread count
    current_unread = conversation.get_unread_count(other_participant)
    conversation.set_unread_count(other_participant, current_unread + 1)
    conversation.save()
    
    return Response(
        MessageSerializer(message).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@renderer_classes([EventStreamRenderer])
def stream_messages_view(request, conversation_id):
    """
    Server-Sent Events endpoint for real-time message updates
    - Requires authentication (supports session or JWT via ?token=)
    - Accepts optional last_id query param to resume stream
    - Emits:
      - event: connected (once)
      - event: new_message (for each new message) with id: <message id>
      - event: heartbeat periodically
      - event: error for errors
    """
    # Try to authenticate via session first; if not authenticated and a token is provided, attempt JWT auth
    print(f"SSE AUTH DEBUG: request.user={request.user}, is_authenticated={getattr(request.user, 'is_authenticated', False)}")
    
    if not request.user or not request.user.is_authenticated:
        token = request.GET.get('token')
        print(f"SSE AUTH DEBUG: token from query params={'present' if token else 'missing'}")
        if token:
            try:
                from rest_framework_simplejwt.authentication import JWTAuthentication
                jwt_auth = JWTAuthentication()
                validated_token = jwt_auth.get_validated_token(token)
                user = jwt_auth.get_user(validated_token)
                print(f"SSE AUTH DEBUG: JWT auth successful, user_id={user.id}, is_staff={user.is_staff}, is_superuser={user.is_superuser}")
                # attach user to request for downstream checks
                request.user = user
            except Exception as e:
                print(f"SSE AUTH DEBUG: JWT auth failed: {e}")
                payload = {"error": "Invalid token"}
                return StreamingHttpResponse(
                    f"event: error\ndata: {json.dumps(payload)}\n\n",
                    content_type='text/event-stream',
                    status=401
                )

    # Validate conversation and membership
    try:
        conversation = Conversation.objects.get(id=conversation_id)
    except Conversation.DoesNotExist:
        payload = {"error": "Conversation not found"}
        return StreamingHttpResponse(
            f"event: error\ndata: {json.dumps(payload)}\n\n",
            content_type='text/event-stream'
        )

    # Check if user is participant OR is admin accessing admin support conversation
    is_participant = conversation.participants.filter(id=request.user.id).exists()
    is_admin_user = getattr(request.user, 'is_staff', False) and getattr(request.user, 'is_superuser', False)
    admin_user = User.objects.filter(is_staff=True, is_superuser=True).first()
    is_admin_conversation = admin_user and conversation.participants.filter(id=admin_user.id).exists()
    
    # Debug logging - use print for immediate visibility
    print(f"SSE DEBUG: user_id={request.user.id}, is_staff={getattr(request.user, 'is_staff', False)}, is_superuser={getattr(request.user, 'is_superuser', False)}, is_participant={is_participant}, is_admin_user={is_admin_user}, is_admin_conversation={is_admin_conversation}, admin_user={admin_user}")
    
    # Allow access if: user is a participant, OR user is admin accessing an admin conversation
    if not (is_participant or (is_admin_user and is_admin_conversation)):
        print(f"SSE DEBUG: Access DENIED for user {request.user.id}")
        payload = {"error": "Access denied"}
        return StreamingHttpResponse(
            f"event: error\ndata: {json.dumps(payload)}\n\n",
            content_type='text/event-stream'
        )
    else:
        print(f"SSE DEBUG: Access GRANTED for user {request.user.id}")

    def event_generator():
        import time
        # Determine start id
        try:
            last_id = int(request.GET.get('last_id')) if request.GET.get('last_id') else None
        except (TypeError, ValueError):
            last_id = None

        if last_id is None:
            last_msg = Message.objects.filter(
                conversation_id=conversation_id,
                deleted_at__isnull=True
            ).order_by('-id').first()
            last_id = last_msg.id if last_msg else 0

        # Initial connect
        yield "event: connected\ndata: {}\nretry: 3000\n\n"

        while True:
            try:
                new_qs = Message.objects.filter(
                    conversation_id=conversation_id,
                    deleted_at__isnull=True,
                    id__gt=last_id
                ).order_by('id')

                for msg in new_qs:
                    data = {
                        'type': 'new_message',
                        'message': MessageSerializer(msg).data
                    }
                    yield f"event: new_message\ndata: {json.dumps(data)}\nid: {msg.id}\n\n"
                    last_id = msg.id

                # heartbeat
                yield "event: heartbeat\ndata: {}\n\n"
                time.sleep(2)
            except GeneratorExit:
                break
            except Exception:
                err = {"error": "Connection error"}
                yield f"event: error\ndata: {json.dumps(err)}\n\n"
                time.sleep(2)
                break

    response = StreamingHttpResponse(event_generator(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_message_reaction_view(request, message_id):
    """Add reaction to a message"""
    try:
        message = Message.objects.get(id=message_id)
    except Message.DoesNotExist:
        return Response({'error': 'Message not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user is participant in conversation
    if not message.conversation.participants.filter(id=request.user.id).exists():
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    reaction = request.data.get('reaction')
    if not reaction:
        return Response({'error': 'Reaction is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Remove existing reaction by this user for this message
    MessageReaction.objects.filter(message=message, user=request.user).delete()
    
    # Add new reaction
    MessageReaction.objects.create(
        message=message,
        user=request.user,
        reaction=reaction
    )
    
    return Response({'message': 'Reaction added'})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def report_message_view(request, message_id):
    """Report a message"""
    try:
        message = Message.objects.get(id=message_id)
    except Message.DoesNotExist:
        return Response({'error': 'Message not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user already reported this message
    if MessageReport.objects.filter(message=message, reporter=request.user).exists():
        return Response({'error': 'Already reported this message'}, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = MessageReportSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    MessageReport.objects.create(
        message=message,
        reporter=request.user,
        **serializer.validated_data
    )
    
    return Response({'message': 'Message reported'})


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_conversation_settings_view(request, conversation_id):
    """Update conversation settings for user"""
    try:
        conversation = Conversation.objects.get(id=conversation_id)
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)
    # Ensure participant
    if not conversation.participants.filter(id=request.user.id).exists():
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    settings, created = ConversationSettings.objects.get_or_create(
        user=request.user,
        conversation=conversation
    )
    
    serializer = ConversationSettingsSerializer(settings, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    
    return Response(ConversationSettingsSerializer(settings).data)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_conversation_permanently_view(request, conversation_id):
    """Permanently delete conversation (admin only)"""
    try:
        conversation = Conversation.objects.get(id=conversation_id)
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Only allow admin users to permanently delete conversations
    if not (getattr(request.user, 'is_staff', False) and getattr(request.user, 'is_superuser', False)):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    # Delete all messages in the conversation
    Message.objects.filter(conversation=conversation).delete()
    
    # Delete the conversation
    conversation.delete()
    
    return Response({'message': 'Conversation permanently deleted'}, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_conversation_view(request, conversation_id):
    """Delete conversation for user (archive)"""
    try:
        conversation = Conversation.objects.get(id=conversation_id)
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)
    # Ensure participant
    if not conversation.participants.filter(id=request.user.id).exists():
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    # Archive conversation for user
    conversation.set_archived(request.user, True)
    conversation.save()
    
    return Response({'message': 'Conversation archived'})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_admin_conversation_view(request):
    """Create a conversation with admin (ReserveWithEase)"""
    try:
        # Find any available admin user (staff + superuser)
        admin_user = User.objects.filter(is_staff=True, is_superuser=True).first()
        print(f"DEBUG: Found admin user: {admin_user}")
        if not admin_user:
            return Response({'error': 'Admin user not found'}, status=status.HTTP_404_NOT_FOUND)
        
        initial_message = request.data.get('message', '')
        subject = request.data.get('subject', 'Support Request')
        print(f"DEBUG: Creating conversation between {request.user} and {admin_user} with subject: {subject}")
        
        if not initial_message:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Always create a new conversation for each new message with subject
        # This ensures separate conversations for different topics
        conversation = Conversation.objects.create(subject=subject)
        conversation.participants.add(request.user, admin_user)
        print(f"DEBUG: Created new conversation: {conversation.id} with subject: {subject}")

        # Send initial message
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            receiver=admin_user,
            content=initial_message,
            message_type='text'
        )
        print(f"DEBUG: Created message: {message.id}")

        conversation.last_message = message
        conversation.save()
        conversation.set_unread_count(admin_user, 1)
        conversation.save()
        print(f"DEBUG: Updated conversation with message and unread count")

        return Response({
            'conversation_id': conversation.id,
            'message': MessageSerializer(message, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        import traceback
        print(f"Error in create_admin_conversation_view: {e}")
        traceback.print_exc()
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_admin_conversation_view(request):
    """Get all conversations with admin for this user"""
    try:
        admin_user = User.objects.filter(is_staff=True, is_superuser=True).first()
        if not admin_user:
            return Response({'error': 'Admin user not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get all conversations between this user and admin
        conversations = Conversation.objects.filter(
            participants=request.user
        ).filter(participants=admin_user).order_by('-updated_at')
        
        if not conversations.exists():
            return Response({'conversations': [], 'messages': []}, status=status.HTTP_200_OK)
        
        # Return all conversations with their data
        conversation_data = []
        for conv in conversations:
            conversation_data.append({
                'id': conv.id,
                'subject': conv.subject,
                'last_message': {
                    'content': conv.last_message.content if conv.last_message else '',
                    'timestamp': conv.last_message.timestamp.isoformat() if conv.last_message else ''
                } if conv.last_message else None,
                'updated_at': conv.updated_at.isoformat()
            })
        
        return Response({
            'conversations': conversation_data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"Error in get_admin_conversation_view: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def admin_conversations_view(request):
    """Get admin support conversations - accessible by both admin users and owners"""
    try:
        user = request.user
        print(f"DEBUG: admin_conversations_view - User {user.id} ({user.username}) is_staff: {getattr(user, 'is_staff', False)} is_superuser: {getattr(user, 'is_superuser', False)}")
        
        # Find admin user
        admin_user = User.objects.filter(is_staff=True, is_superuser=True).first()
        if not admin_user:
            return Response({'error': 'Admin user not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # If user is admin, show all admin support conversations
        if getattr(user, 'is_staff', False) and getattr(user, 'is_superuser', False):
            conversations = Conversation.objects.filter(
                participants=admin_user
            ).filter(
                participants__role__in=['owner', 'single_owner']
            ).distinct().order_by('-updated_at')
        else:
            # If user is owner, show only their conversations with admin
            conversations = Conversation.objects.filter(
                participants=user
            ).filter(
                participants=admin_user
            ).distinct().order_by('-updated_at')
        
        print(f"DEBUG: Found {conversations.count()} conversations")
        for conv in conversations:
            participants = conv.participants.all()
            print(f"DEBUG: Conversation {conv.id} participants: {[p.username for p in participants]}")
        
        serializer = ConversationSerializer(conversations, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error in admin_conversations_view: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_message_view(request, conversation_id):
    """Send a message in a conversation"""
    try:
        conversation = Conversation.objects.get(id=conversation_id)
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user is participant OR admin accessing admin support conversation
    is_participant = conversation.participants.filter(id=request.user.id).exists()
    admin_user = User.objects.filter(is_staff=True, is_superuser=True).first()
    is_admin_conversation = admin_user and conversation.participants.filter(id=admin_user.id).exists()
    
    if not (is_participant or is_admin_conversation):
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    content = request.data.get('content')
    if not content:
        return Response({'error': 'Message content is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Get other participant - if admin conversation, get the owner
    if is_admin_conversation and not is_participant:
        # Current user is admin, get the owner participant
        other_participant = conversation.participants.exclude(id=admin_user.id).first()
        sender = admin_user  # Admin sends the message
    else:
        # Regular participant flow
        other_participant = conversation.participants.exclude(id=request.user.id).first()
        sender = request.user
        
    if not other_participant:
        return Response({'error': 'Conversation has no other participants'}, status=status.HTTP_400_BAD_REQUEST)

    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        receiver=other_participant,
        content=content,
        message_type=request.data.get('message_type', 'text')
    )

    # Update conversation
    conversation.last_message = message
    conversation.save()

    # Update unread count
    current_unread = conversation.get_unread_count(other_participant)
    conversation.set_unread_count(other_participant, current_unread + 1)
    conversation.save()

    return Response(
        MessageSerializer(message).data,
        status=status.HTTP_201_CREATED
    )
