from django.contrib import admin
from .models import User, Chatbot, ChatbotDocument, Conversation, Message, Contact

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'name', 'email', 'created_at')
    search_fields = ('user_id', 'name', 'email')
    readonly_fields = ('user_id', 'created_at')

@admin.register(Chatbot)
class ChatbotAdmin(admin.ModelAdmin):
    list_display = ('chatbot_id', 'user', 'name', 'status', 'dataset_name', 'created_at')
    search_fields = ('chatbot_id', 'name', 'description', 'dataset_name')
    list_filter = ('user', 'status')

@admin.register(ChatbotDocument)
class ChatbotDocumentAdmin(admin.ModelAdmin):
    list_display = ('chatbot', 'document', 'uploaded_at')
    search_fields = ('chatbot__name', 'document')  # Search by chatbot name and document
    list_filter = ('chatbot',)

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('chatbot', 'user_id', 'started_at', 'last_updated')
    search_fields = ('chatbot__name', 'user_id')
    list_filter = ('chatbot',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'content', 'is_bot', 'timestamp')
    search_fields = ('conversation__chatbot__name', 'content')  # Search by chatbot name and content
    list_filter = ('conversation', 'is_bot')

class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'interest', 'is_responded', 'created_at')  # Include 'interest' and 'is_responded'
    list_filter = ('interest', 'is_responded', 'created_at')  # Include 'interest' and 'is_responded'
    search_fields = ('name', 'email', 'phone', 'message')

admin.site.register(Contact, ContactAdmin)