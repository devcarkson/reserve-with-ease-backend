from rest_framework import serializers
from .models import Notification, EmailTemplate, EmailNotification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'


class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = '__all__'


class EmailNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailNotification
        fields = '__all__'