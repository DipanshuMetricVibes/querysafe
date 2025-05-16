from django.contrib import admin
from django.utils.html import format_html
from .models import User, Chatbot, ChatbotDocument, Conversation, Message, Contact, ActivationCode, SubscriptionPlan, UserPlanAlot, HelpSupportRequest

@admin.register(ActivationCode)
class ActivationCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'times_used', 'usage_count', 'is_valid', 'created_at')
    list_filter = ('created_at', 'times_used')
    search_fields = ('code',)
    readonly_fields = ('times_used', 'created_at')
    ordering = ('-created_at',)

    def usage_count(self, obj):
        return f"{obj.times_used}/5"
    usage_count.short_description = 'Usage Count'

    def is_valid(self, obj):
        return obj.times_used < 5
    is_valid.boolean = True
    is_valid.short_description = 'Is Valid'

    def has_change_permission(self, request, obj=None):
        # Prevent editing of fully used activation codes
        if obj and obj.times_used >= 5:
            return False
        return True

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'name', 'email', 'registration_status', 'is_active', 'created_at')
    list_filter = ('is_active', 'registration_status', 'created_at')
    search_fields = ('name', 'email', 'user_id')
    readonly_fields = ('user_id', 'created_at', 'otp_verified_at', 'activated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('user_id', 'name', 'email', 'password')
        }),
        ('Status Information', {
            'fields': ('is_active', 'registration_status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'otp_verified_at', 'activated_at')
        }),
    )

@admin.register(Chatbot)
class ChatbotAdmin(admin.ModelAdmin):
    list_display = ('chatbot_id', 'user', 'name', 'status_badge', 'dataset_name', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('chatbot_id', 'name', 'description', 'dataset_name')
    readonly_fields = ('chatbot_id', 'created_at')

    def status_badge(self, obj):
        colors = {
            'training': 'warning',
            'active': 'success',
            'inactive': 'danger',
            'failed': 'danger'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            obj.status.title()
        )
    status_badge.short_description = 'Status'

@admin.register(ChatbotDocument)
class ChatbotDocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'chatbot', 'document_name', 'uploaded_at')
    list_filter = ('uploaded_at', 'chatbot')
    search_fields = ('chatbot__name', 'document')
    readonly_fields = ('uploaded_at',)

    def document_name(self, obj):
        try:
            if hasattr(obj.document, 'name'):
                return obj.document.name.split('/')[-1]
            elif isinstance(obj.document, str):
                return obj.document.split('/')[-1]
            return str(obj.document)
        except Exception:
            return 'No document'
    document_name.short_description = 'Document'

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'chatbot', 'user_id', 'message_count', 'started_at', 'last_updated')
    list_filter = ('started_at', 'last_updated')
    search_fields = ('chatbot__name', 'user_id')
    readonly_fields = ('started_at', 'last_updated')

    def message_count(self, obj):
        try:
            # Using the related_name 'messages' from the Message model
            return obj.messages.count()
        except Exception:
            return 0
    message_count.short_description = 'Messages'

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'short_content', 'is_bot', 'timestamp')
    list_filter = ('is_bot', 'timestamp', 'conversation__chatbot')
    search_fields = ('content', 'conversation__chatbot__name')
    readonly_fields = ('timestamp',)

    def short_content(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    short_content.short_description = 'Content'

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'interest', 'short_message', 'is_responded', 'created_at')
    list_filter = ('interest', 'is_responded', 'created_at')
    search_fields = ('name', 'email', 'phone', 'message')
    readonly_fields = ('created_at',)

    def short_message(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    short_message.short_description = 'Message'

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        'plan_id', 
        'plan_name', 
        'start_date', 
        'no_of_bot', 
        'no_query_per_bot', 
        'no_of_docs_per_bot', 
        'size_limit_per_docs', 
        'pricing', 
        'status', 
        'timestamp'
    )
    search_fields = ('plan_name',)
    list_filter = ('start_date', 'timestamp', 'status')


@admin.register(UserPlanAlot)
class UserPlanAlotAdmin(admin.ModelAdmin):
    list_display = (
        'plan_alot_id', 
        'user', 
        'plan_name', 
        'start_date', 
        'no_of_bot', 
        'no_query', 
        'no_of_docs', 
        'doc_size_limit', 
        'expire_date', 
        'timestamp'
    )
    search_fields = ('plan_name', 'user__user_id')
    list_filter = ('start_date', 'expire_date', 'timestamp')

@admin.register(HelpSupportRequest)
class HelpSupportRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'message_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__name', 'user__email', 'subject', 'message')

    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'