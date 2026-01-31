from django.urls import path
from . import views
from .sse_views import message_stream

app_name = 'messaging'

urlpatterns = [
    path('conversations/', views.ConversationListView.as_view(), name='conversation-list'),
    path('conversations/create/', views.create_conversation_view, name='create-conversation'),
    path('conversations/admin/create/', views.create_admin_conversation_view, name='create-admin-conversation'),
    path('conversations/admin/', views.get_admin_conversation_view, name='get-admin-conversation'),
    path('conversations/admin/list/', views.admin_conversations_view, name='admin-conversations'),
    path('conversations/debug-create/', views.debug_create_test_conversation, name='debug-create-conversation'),
    path('conversations/<int:pk>/', views.ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<int:conversation_id>/messages/', views.MessageListView.as_view(), name='message-list'),
    path('conversations/<int:conversation_id>/send/', views.send_message_view, name='send-message'),
    path('conversations/<int:conversation_id>/read/', views.mark_messages_read_view, name='mark-messages-read'),
    path('conversations/<int:conversation_id>/upload/', views.upload_message_attachment_view, name='upload-message-attachment'),
    path('messages/<int:message_id>/react/', views.add_message_reaction_view, name='add-message-reaction'),
    path('messages/<int:message_id>/report/', views.report_message_view, name='report-message'),
    path('conversations/<int:conversation_id>/settings/', views.update_conversation_settings_view, name='update-conversation-settings'),
    path('conversations/<int:conversation_id>/stream/', message_stream, name='message-stream'),
    path('conversations/<int:conversation_id>/archive/', views.delete_conversation_view, name='archive-conversation'),
    path('conversations/<int:conversation_id>/delete/', views.delete_conversation_permanently_view, name='delete-conversation'),
]
