from django.contrib import admin
from .models import Conversation, Message, MessageAttachment, MessageReaction, ConversationSettings, MessageReport

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_participants', 'last_message', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('participants__username', 'participants__email')
    readonly_fields = ('created_at', 'updated_at')

    def get_participants(self, obj):
        return ", ".join([user.username for user in obj.participants.all()])
    get_participants.short_description = 'Participants'

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'receiver', 'content_preview', 'timestamp', 'read_at', 'message_type')
    list_filter = ('message_type', 'timestamp', 'read_at')
    search_fields = ('sender__username', 'receiver__username', 'content')
    readonly_fields = ('timestamp', 'read_at')

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'

@admin.register(MessageAttachment)
class MessageAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'filename', 'file_size', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('filename', 'message__content')

@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'user', 'reaction', 'created_at')
    list_filter = ('reaction', 'created_at')
    search_fields = ('user__username', 'message__content')

@admin.register(ConversationSettings)
class ConversationSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'conversation', 'notifications_enabled', 'muted')
    list_filter = ('notifications_enabled', 'muted')
    search_fields = ('user__username', 'conversation__id')

@admin.register(MessageReport)
class MessageReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'reporter', 'reason', 'resolved', 'created_at')
    list_filter = ('reason', 'resolved', 'created_at')
    search_fields = ('reporter__username', 'message__content')
