from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, Message, MessageAttachment, MessageReaction, ConversationSettings, MessageReport

User = get_user_model()


class MessageAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageAttachment
        fields = '__all__'


class MessageReactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageReaction
        fields = '__all__'


class ConversationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationSettings
        fields = '__all__'


class MessageReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageReport
        fields = '__all__'


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_avatar = serializers.ImageField(source='sender.profile_picture', read_only=True)
    receiver_name = serializers.CharField(source='receiver.get_full_name', read_only=True)
    receiver_avatar = serializers.ImageField(source='receiver.profile_picture', read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    reactions = MessageReactionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ('sender', 'receiver', 'timestamp')


class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ('content', 'message_type')


class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'role')


class ConversationSerializer(serializers.ModelSerializer):
    participants = UserBasicSerializer(many=True, read_only=True)
    last_message = MessageSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    property = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = '__all__'
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_unread_count(request.user)
        return 0

    def get_property(self, obj):
        try:
            from reservations.models import Reservation
            users = list(obj.participants.all())
            print(f"DEBUG: Conversation {obj.id} participants: {[u.username for u in users]}")
            if len(users) != 2:
                return None
            u1, u2 = users
            res = (
                Reservation.objects
                .filter(user__in=[u1, u2], property_obj__owner__in=[u1, u2])
                .order_by('-created_at')
                .first()
            )
            if res:
                prop_data = {
                    'id': res.property_obj.id,
                    'name': res.property_obj.name
                }
                print(f"DEBUG: Found property: {prop_data}")
                return prop_data
            print(f"DEBUG: No property found for conversation {obj.id}")
            return None
        except Exception as e:
            print(f"DEBUG: Error getting property: {e}")
            return None


class ConversationCreateSerializer(serializers.ModelSerializer):
    initial_message = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = Conversation
        fields = ()


class ConversationDetailSerializer(ConversationSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Conversation
        fields = '__all__'
