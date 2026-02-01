from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class HelpContact(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    subject = models.CharField(max_length=500)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.subject}"


class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    subject = models.CharField(max_length=255, blank=True, default='')  # Add subject field
    last_message = models.OneToOneField(
        'Message', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='conversation_last'
    )
    unread_count = models.JSONField(default=dict)  # Store unread count per user
    is_archived = models.JSONField(default=dict)  # Store archive status per user
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        participants_names = ', '.join([user.username for user in self.participants.all()])
        return f"Conversation between {participants_names}"
    
    def get_unread_count(self, user):
        return self.unread_count.get(str(user.id), 0)
    
    def set_unread_count(self, user, count):
        self.unread_count[str(user.id)] = count
        self.save(update_fields=['unread_count'])
    
    def is_user_archived(self, user):
        return self.is_archived.get(str(user.id), False)
    
    def set_archived(self, user, archived):
        self.is_archived[str(user.id)] = archived
        self.save(update_fields=['is_archived'])
    
    def get_other_participant(self, user):
        return self.participants.exclude(id=user.id).first()


class Message(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
        ('system', 'System'),
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES, default='text')
    attachment_url = models.URLField(blank=True)
    attachment_name = models.CharField(max_length=255, blank=True)
    attachment_size = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username}"
    
    @property
    def is_read(self):
        return self.read_at is not None
    
    def mark_as_read(self):
        from django.utils import timezone
        if not self.read_at:
            self.read_at = timezone.now()
            self.save(update_fields=['read_at'])
            
            # Update conversation unread count
            self.receiver_conversation.unread_count[str(self.receiver.id)] = max(
                0, self.receiver_conversation.get_unread_count(self.receiver) - 1
            )
            self.receiver_conversation.save(update_fields=['unread_count'])
    
    @property
    def receiver_conversation(self):
        # Get the conversation from receiver's perspective
        return Conversation.objects.filter(
            id=self.conversation_id,
            participants=self.receiver
        ).first()


class MessageReadReceipt(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_receipts')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['message', 'user']
    
    def __str__(self):
        return f"Read receipt for Message {self.message.id} by {self.user.username}"


class MessageAttachment(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='message_attachments/')
    filename = models.CharField(max_length=255)
    file_size = models.IntegerField()
    file_type = models.CharField(max_length=100)
    thumbnail = models.ImageField(upload_to='message_thumbnails/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Attachment {self.filename} for Message {self.message.id}"


class MessageReaction(models.Model):
    REACTION_CHOICES = [
        ('like', '👍'),
        ('love', '❤️'),
        ('laugh', '😂'),
        ('wow', '😮'),
        ('sad', '😢'),
        ('angry', '😠'),
    ]
    
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction = models.CharField(max_length=10, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['message', 'user', 'reaction']
    
    def __str__(self):
        return f"{self.reaction} reaction by {self.user.username} on Message {self.message.id}"


class ConversationSettings(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    muted = models.BooleanField(default=False)
    muted_until = models.DateTimeField(null=True, blank=True)
    pinned = models.BooleanField(default=False)
    notifications_enabled = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'conversation']
    
    def __str__(self):
        return f"Settings for {self.user.username} in Conversation {self.conversation.id}"
    
    @property
    def is_muted(self):
        from django.utils import timezone
        if not self.muted:
            return False
        if self.muted_until and self.muted_until <= timezone.now():
            self.muted = False
            self.muted_until = None
            self.save(update_fields=['muted', 'muted_until'])
            return False
        return True


class MessageReport(models.Model):
    REASON_CHOICES = [
        ('spam', 'Spam'),
        ('inappropriate', 'Inappropriate Content'),
        ('harassment', 'Harassment'),
        ('threat', 'Threat'),
        ('other', 'Other'),
    ]
    
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    details = models.TextField(blank=True)
    resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='resolved_message_reports'
    )
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['message', 'reporter']
    
    def __str__(self):
        return f"Report by {self.reporter.username} for Message {self.message.id}"


class MessageTemplate(models.Model):
    TEMPLATE_TYPE_CHOICES = [
        ('welcome', 'Welcome Message'),
        ('booking_confirmation', 'Booking Confirmation'),
        ('check_in_reminder', 'Check-in Reminder'),
        ('check_out_reminder', 'Check-out Reminder'),
        ('review_request', 'Review Request'),
        ('custom', 'Custom'),
    ]
    
    name = models.CharField(max_length=255)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPE_CHOICES)
    subject = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    variables = models.JSONField(default=list)  # List of variable names
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Template: {self.name}"


class MessageAnalytics(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='analytics')
    date = models.DateField()
    messages_sent = models.IntegerField(default=0)
    response_time_minutes = models.FloatField(default=0)
    engagement_rate = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['conversation', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"Analytics for Conversation {self.conversation.id} on {self.date}"
