from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.http import StreamingHttpResponse
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
        qs = Conversation.objects.filter(participants=user).distinct()
        participant_type = self.request.query_params.get('participant_type')
        # Filter for owners to show only conversations with guests when requested
        if participant_type == 'guest' and getattr(user, 'role', None) == 'owner':
            qs = qs.filter(participants__role='user').distinct()
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
        unread_count = Message.objects.filter(
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
        from rest_framework.exceptions import PermissionDenied
        conversation_id = self.kwargs['conversation_id']
        # Ensure the requester is a participant
        try:
            conv = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Message.objects.none()
        if not conv.participants.filter(id=self.request.user.id).exists():
            raise PermissionDenied("Not a participant of this conversation")
        return Message.objects.filter(
            conversation_id=conversation_id,
            deleted_at__isnull=True
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_conversation_view(request):
    """Create a new conversation"""
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
        return Response(
            ConversationSerializer(existing_conversation).data,
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
            MessageSerializer(message).data,
            status=status.HTTP_201_CREATED
        )

    return Response(
        ConversationSerializer(conversation).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_messages_read_view(request, conversation_id):
    """Mark all messages in conversation as read"""
    try:
        conversation = Conversation.objects.get(id=conversation_id)
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)
    # Ensure participant
    if not conversation.participants.filter(id=request.user.id).exists():
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
        attachment_size=attachment.size,
        file_type=attachment.content_type
    )
    
    # Create attachment record
    MessageAttachment.objects.create(
        message=message,
        file=attachment,
        filename=attachment.name,
        file_size=attachment.size,
        file_type=attachment.content_type
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


def stream_messages_view(request, conversation_id):
    """
    Server-Sent Events endpoint for real-time message updates
    """
    print(f"SSE: Starting stream for conversation {conversation_id}, user {request.user.id}")

    try:
        conversation = Conversation.objects.get(id=conversation_id)
    except Conversation.DoesNotExist:
        print(f"SSE: Conversation {conversation_id} not found")
        return StreamingHttpResponse(
            f"data: {{\"error\": \"Conversation not found\"}}\n\n",
            content_type='text/event-stream'
        )

    # Check if user is participant
    if not conversation.participants.filter(id=request.user.id).exists():
        print(f"SSE: User {request.user.id} not participant in conversation {conversation_id}")
        return StreamingHttpResponse(
            f"data: {{\"error\": \"Access denied\"}}\n\n",
            content_type='text/event-stream'
        )

    print(f"SSE: Stream established for user {request.user.id} in conversation {conversation_id}")

    def event_generator():
        # Initialize with current message count
        messages = Message.objects.filter(
            conversation_id=conversation_id,
            deleted_at__isnull=True
        ).order_by('timestamp')
        last_message_count = messages.count()

        while True:
            try:
                # Get current messages
                messages = Message.objects.filter(
                    conversation_id=conversation_id,
                    deleted_at__isnull=True
                ).order_by('timestamp')

                current_count = messages.count()

                # If new messages arrived, send them
                if current_count > last_message_count:
                    print(f"SSE: Detected {current_count - last_message_count} new messages")
                    new_messages = messages[last_message_count:]
                    for message in new_messages:
                        try:
                            message_data = MessageSerializer(message).data
                            print(f"SSE: Sending message {message.id} to user {request.user.id}")
                            yield f"data: {{\"type\": \"new_message\", \"message\": {message_data}}}\n\n"
                        except Exception as e:
                            print(f"SSE: Serialization error: {str(e)}")
                            yield f"data: {{\"error\": \"Serialization error: {str(e)}\"}}\n\n"

                    last_message_count = current_count

                # Send heartbeat to keep connection alive
                yield f"data: {{\"type\": \"heartbeat\"}}\n\n"

                # Wait before checking again
                import time
                time.sleep(1)

            except Exception as e:
                yield f"data: {{\"error\": \"Connection error\"}}\n\n"
                break

    response = StreamingHttpResponse(
        event_generator(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
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
def send_message_view(request, conversation_id):
    """Send a message in a conversation"""
    try:
        conversation = Conversation.objects.get(id=conversation_id)
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)
    # Ensure participant
    if not conversation.participants.filter(id=request.user.id).exists():
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    content = request.data.get('content')
    if not content:
        return Response({'error': 'Message content is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Get other participant
    other_participant = conversation.participants.exclude(id=request.user.id).first()
    if not other_participant:
        return Response({'error': 'Conversation has no other participants'}, status=status.HTTP_400_BAD_REQUEST)

    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
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
