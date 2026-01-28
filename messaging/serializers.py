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


class ConversationSerializer(serializers.ModelSerializer):
    participants = serializers.StringRelatedField(many=True, read_only=True)
    last_message = MessageSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = '__all__'
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_unread_count(request.user)
        return 0


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
