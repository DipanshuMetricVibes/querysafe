from django.db import models
import random
import string
import os
from django.conf import settings
# from django.core.files.storage import default_storage
from django.utils.text import get_valid_filename
import threading
import fitz  # PyMuPDF
from user_askVibes.vectorization.pipeline_processor import run_pipeline_background
from django.contrib.auth import get_user_model
User = get_user_model()

class User(models.Model):
    user_id = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.user_id:
            # Generate random alphanumeric string of length 3-6
            random_string = ''.join(random.choices(string.ascii_uppercase + string.digits, k=random.randint(3,6)))
            self.user_id = f"PC{random_string}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

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
    js.src = "{base_url}/widget/{self.chatbot_id}/askvibes.js";
    js.async = true;
    fjs.parentNode.insertBefore(js, fjs);
}}(window, document, 'script', 'askvibes-widget'));
</script>'''

    @property
    def conversation_count(self):
        return self.conversations.count()

    def __str__(self):
        return self.name

class ChatbotDocument(models.Model):
    chatbot = models.ForeignKey(Chatbot, on_delete=models.CASCADE, related_name='documents')
    document = models.CharField(max_length=255, blank=True, null=True)  # Store the file path as a string
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.document if self.document else "No document"

    def save(self, *args, **kwargs):
        is_new = not self.pk and hasattr(self, 'pdf_file')
        if is_new:  # Check if it's a new instance and pdf_file exists
            pdf_file = self.pdf_file
            chatbot_id = self.chatbot.chatbot_id
            original_filename = get_valid_filename(pdf_file.name)
            file_extension = os.path.splitext(original_filename)[1]

            # Truncate the original filename if it's too long
            max_filename_length = 200  # Adjust as needed
            if len(original_filename) > max_filename_length:
                original_filename = original_filename[:max_filename_length - len(file_extension)]

            filename = f"{chatbot_id}_{original_filename}{file_extension}"
            
            upload_path = os.path.join('documents', 'files_uploaded', filename)
            full_path = os.path.join(settings.BASE_DIR, upload_path)

            # Ensure the directory exists
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            # Save the file
            with open(full_path, 'wb+') as destination:
                for chunk in pdf_file.chunks():
                    destination.write(chunk)

            self.document = upload_path  # Store the file path
            print(f"✅ File uploaded: {filename}")
        super().save(*args, **kwargs)
        
        # Start the pipeline in a single background thread
        # if is_new:
        #     threading.Thread(
        #         target=process_chatbot_pipeline,
        #         args=(self.chatbot.chatbot_id,),
        #         daemon=True
        #     ).start()
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

def process_chatbot_pipeline(chatbot_id):
    # 1. PDF to Images
    pdf_dir = os.path.join("documents", "files_uploaded")
    img_dir = os.path.join("documents", "files_images")
    pdf_files = [f for f in os.listdir(pdf_dir) if f.startswith(chatbot_id + "_") and f.lower().endswith(".pdf")]
    for pdf_file in pdf_files:
        # Convert PDF to images
        pdf_path = os.path.join(pdf_dir, pdf_file)
        print(f"Converting {pdf_file} to images...")
        # (Call your PDF-to-image function here, e.g., convert_pdf_to_images(pdf_path, img_dir))
        print(f"PDF {pdf_file} converted to images successfully.")
    print("All PDFs converted to images.")

    # 2. Images to Captions
    img_files = [f for f in os.listdir(img_dir) if f.startswith(chatbot_id + "_") and f.lower().endswith(".png")]
    # Group images by PDF base name
    from collections import defaultdict
    pdf_images = defaultdict(list)
    for img_file in img_files:
        base = "_".join(img_file.split("_")[:-1])
        pdf_images[base].append(img_file)
    for base, images in pdf_images.items():
        print(f"Generating captions for {base}...")
        # (Call your image-to-caption function here, e.g., process_images_to_text(chatbot_id, images))
        print(f"Captions generated for {base}.")
    print("All images captioned.")

    # 3. Caption to Chunk
    caption_dir = os.path.join("documents", "files_captions")
    caption_files = [f for f in os.listdir(caption_dir) if f.startswith(chatbot_id + "_") and f.endswith(".txt")]
    for caption_file in caption_files:
        print(f"Chunking {caption_file}...")
        # (Call your chunking function here, e.g., chunk_text_file(input_path, output_path))
        print(f"Chunked {caption_file}.")
    print("All caption files chunked.")

    # 4. Merge and Embed
    print("Merging all chunks and embedding...")
    # (Call your embedding function here, e.g., process_all_chunk_files(chatbot_id))
    print(f"All chunks merged and embedded for chatbot {chatbot_id}.")

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