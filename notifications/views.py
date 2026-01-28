from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .models import Notification, EmailTemplate, EmailNotification
from .serializers import NotificationSerializer, EmailTemplateSerializer

User = get_user_model()


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_notification_read_view(request, notification_id):
    """Mark a notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.mark_as_read()
        return Response({'message': 'Notification marked as read'})
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_all_notifications_read_view(request):
    """Mark all notifications as read for the user"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({'message': 'All notifications marked as read'})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notification_count_view(request):
    """Get unread notification count"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return Response({'unread_count': count})


# Email template management (admin only)
class EmailTemplateListView(generics.ListCreateAPIView):
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    permission_classes = [permissions.IsAdminUser]


class EmailTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    permission_classes = [permissions.IsAdminUser]