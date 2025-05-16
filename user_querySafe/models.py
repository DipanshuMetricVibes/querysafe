from django.db import models
import random
import string
import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.text import get_valid_filename
from user_querySafe.chatbot.pipeline_processor import run_pipeline_background
from django.contrib.auth import get_user_model
User = get_user_model()

# Create a custom storage that points to BASE_DIR/documents/files_uploaded
custom_storage = FileSystemStorage(location=os.path.join(settings.BASE_DIR, 'documents', 'files_uploaded'))

class User(models.Model):
    STATUS_CHOICES = (
        ('registered', 'Registered'),
        ('otp_verified', 'OTP Verified'),
        ('activated', 'Activated')
    )

    user_id = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    is_active = models.BooleanField(default=False)
    registration_status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES,
        default='registered'
    )
    otp_verified_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.user_id:
            # Generate random alphanumeric string of length 3-6
            random_string = ''.join(random.choices(string.ascii_uppercase + string.digits, k=random.randint(3,6)))
            self.user_id = f"PC{random_string}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class ActivationCode(models.Model):
    code = models.CharField(max_length=8, unique=True)  # Changed to 8 for alphanumeric
    times_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} (Used: {self.times_used}/10)"

    @property
    def is_used(self):
        return self.times_used >= 10

    def save(self, *args, **kwargs):
        if not self.code:
            # Generate random 8-character alphanumeric code in uppercase
            while True:
                new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                if not ActivationCode.objects.filter(code=new_code).exists():
                    self.code = new_code
                    break
        super().save(*args, **kwargs)

class EmailOTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def is_valid(self):
        # OTP valid for 10 minutes
        from django.utils import timezone
        return (timezone.now() - self.created_at).total_seconds() < 600

class Chatbot(models.Model):
    chatbot_id = models.CharField(max_length=6, unique=True, editable=False)
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='chatbots')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='training')
    logo = models.ImageField(
        upload_to='chatbot_logos/',
        blank=True, 
        null=True
    )
    dataset_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.chatbot_id:
            while True:
                random_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                if not Chatbot.objects.filter(chatbot_id=random_id).exists():
                    self.chatbot_id = random_id
                    break
        super().save(*args, **kwargs)

    def logo_file_name(self):
        if self.logo:
            return f"{self.chatbot_id}_{self.logo.name}"
        return None

    @property
    def snippet_code(self):
        # Get the base URL from settings or environment variable
        from django.conf import settings
        base_url = getattr(settings, 'WEBSITE_URL')
        
        return f'''<script>
        (function(w,d,s,id){{
            var js, fjs = d.getElementsByTagName(s)[0];
            if (d.getElementById(id)){{return;}}
            js = d.createElement(s);
            js.id = id;
            js.src = "{base_url}/widget/{self.chatbot_id}/querySafe.js";
            js.async = true;
            fjs.parentNode.insertBefore(js, fjs);
        }}(window, document, 'script', 'querySafe-widget'));
        </script>'''

    @property
    def conversation_count(self):
        return self.conversations.count()

    def __str__(self):
        return self.name

class ChatbotDocument(models.Model):
    chatbot = models.ForeignKey('Chatbot', on_delete=models.CASCADE)
    # Use custom_storage so that files are saved in BASE_DIR/documents/files_uploaded
    document = models.FileField(upload_to='', storage=custom_storage)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.document.name) if hasattr(self.document, 'name') else "No document"

    def save(self, *args, **kwargs):
        # If new and file is uploaded, rename the file before saving
        if not self.pk and self.document:
            pdf_file = self.document
            chatbot_id = self.chatbot.chatbot_id
            original_filename = get_valid_filename(pdf_file.name)
            file_extension = os.path.splitext(original_filename)[1]

            # Truncate the original filename if it's too long
            max_filename_length = 200
            if len(original_filename) > max_filename_length:
                original_filename = original_filename[:max_filename_length - len(file_extension)]

            filename = f"{chatbot_id}_{original_filename}{file_extension}"
            # Save file using custom storage (this writes to BASE_DIR/documents/files_uploaded)
            saved_name = self.document.storage.save(filename, pdf_file)
            self.document.name = saved_name
            print(f"✅ File uploaded: {filename}")

        super().save(*args, **kwargs)
        run_pipeline_background(self.chatbot.chatbot_id)

class Conversation(models.Model):
    conversation_id = models.CharField(max_length=10, unique=True, editable=False)
    chatbot = models.ForeignKey(Chatbot, on_delete=models.CASCADE, related_name='conversations')
    user_id = models.CharField(max_length=100)  # Session or user identifier
    started_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.conversation_id:
            # Generate unique conversation ID
            while True:
                conv_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
                if not Conversation.objects.filter(conversation_id=conv_id).exists():
                    self.conversation_id = conv_id
                    break
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-last_updated']

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    is_bot = models.BooleanField(default=False)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']


class Activity(models.Model):
    ACTIVITY_TYPES = (
        ('primary', 'Primary'),
        ('success', 'Success'), 
        ('info', 'Info'),
        ('warning', 'Warning')
    )

    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='activities')
    type = models.CharField(max_length=20, choices=ACTIVITY_TYPES, default='primary')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='info')  # Material icon name
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Activities'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.name} - {self.title}"

    @classmethod
    def log(cls, user, title, description='', activity_type='primary', icon='info'):
        return cls.objects.create(
            user=user,
            title=title,
            description=description,
            type=activity_type,
            icon=icon
        )

class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField()
    interest = models.CharField(max_length=50, blank=True, null=True)  # Add this field
    is_responded = models.BooleanField(default=False)  # Add this field
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.email}"

    class Meta:
        ordering = ['-created_at']

class SubscriptionPlan(models.Model):
    plan_id = models.CharField(max_length=5, unique=True, primary_key=True)
    plan_name = models.CharField(max_length=255)
    start_date = models.DateField()
    no_of_bot = models.PositiveIntegerField()
    no_query_per_bot = models.PositiveIntegerField()
    no_of_docs_per_bot = models.PositiveIntegerField()
    size_limit_per_docs = models.PositiveIntegerField(help_text="Size limit per document in units (e.g., MB)")
    pricing = models.DecimalField(max_digits=8, decimal_places=2, help_text="Plan pricing (e.g., in USD)", default=0.00)
    STATUS_CHOICES = (
        ('public', 'Public'),
        ('limited', 'Limited'),
        ('private', 'Private'),
        ('personal', 'Personal'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='public')
    timestamp = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.plan_id:
            # Generate a unique 5-digit alphanumeric id
            while True:
                new_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
                if not SubscriptionPlan.objects.filter(plan_id=new_id).exists():
                    self.plan_id = new_id
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return self.plan_name

class UserPlanAlot(models.Model):
    plan_alot_id = models.CharField(max_length=14, unique=True, primary_key=True)
    user = models.ForeignKey(User, to_field='user_id', on_delete=models.CASCADE)
    plan_name = models.CharField(max_length=255)
    start_date = models.DateField()
    no_of_bot = models.PositiveIntegerField()
    no_query = models.PositiveIntegerField()
    no_of_docs = models.PositiveIntegerField()
    doc_size_limit = models.PositiveIntegerField(help_text="Document size limit in MB")
    expire_date = models.DateField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.plan_alot_id:
            # Generate a unique 8-digit alphanumeric id
            while True:
                new_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                if not UserPlanAlot.objects.filter(plan_alot_id=new_id).exists():
                    self.plan_alot_id = new_id
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.plan_name}"

class HelpSupportRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="help_requests")
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} - {self.subject}"