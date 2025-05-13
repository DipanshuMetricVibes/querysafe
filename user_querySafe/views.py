from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import RegisterForm, LoginForm, ChatbotCreateForm, OTPVerificationForm
from .models import ActivationCode, Activity, Contact, User, Chatbot, ChatbotDocument, Conversation, Message, EmailOTP, UserPlanAlot, SubscriptionPlan
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
import os
import faiss
from sentence_transformers import SentenceTransformer
from google import genai
from django.conf import settings
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count
from django.core.mail import send_mail
import random
from django.template.loader import render_to_string
from .decorators import redirect_authenticated_user, login_required
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.urls import reverse

# Initialize models and clients
embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
client = genai.Client(vertexai=True, project=settings.PROJECT_ID, location=settings.REGION)

def generate_otp():
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])

def send_otp_email(email, otp, name, verification_url):
    try:
        subject = 'Verify Your Account'
        
        # Render the HTML template with personalized details
        html_message = render_to_string('user_querySafe/email/registration-otp.html', {
            'otp': otp,
            'name': name,
            'verification_url': verification_url,
            'project_name': settings.PROJECT_NAME
        })
        
        # Create plain-text fallback message with a clickable URL
        plain_message = (
            f"Hello {name},\n\n"
            f"Your OTP is: {otp}\n\n"
            f"Click the following link to verify your account:\n"
            f"{verification_url}\n\n"
            "The OTP is valid for 10 minutes."
        )
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def send_welcome_email(email, name, dashboard_url):
    try:
        subject = "Welcome to QuerySafe"
        html_message = render_to_string("user_querySafe/email/welcome-user.html", {
            'name': name,
            'dashboard_url': dashboard_url,
            'project_name': settings.PROJECT_NAME
        })
        plain_message = (
            f"Hello {name},\n\n"
            f"Welcome to QuerySafe!\n"
            f"Access your dashboard here: {dashboard_url}\n\n"
            "Thank you for joining us."
        )
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending welcome email: {str(e)}")
        return False

@redirect_authenticated_user
def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        email = request.POST.get('email')
        
        # Check if user exists and registration is incomplete
        try:
            existing_user = User.objects.get(email=email)
            request.session['pending_activation_user_id'] = existing_user.user_id

            if existing_user.registration_status == 'registered':
                messages.info(request, 'Please complete your email verification.')
                return redirect('verify_otp')
            elif existing_user.registration_status == 'otp_verified':
                messages.info(request, 'Please complete your account activation.')
                return redirect('verify_activation')
            elif not existing_user.is_active:
                messages.info(request, 'Please activate your account.')
                return redirect('verify_activation')
            else:
                messages.error(request, 'Email already registered! Please login.')
                return redirect('login')
        except User.DoesNotExist:
            pass

        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        if password != confirm_password:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'user_querySafe/register.html', {'form': form})
            
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already registered!')
                return render(request, 'user_querySafe/register.html', {'form': form})

            user = User.objects.create(
                name=name,
                email=email,
                password=password,
                is_active=False,
                registration_status='registered'
            )

            otp = generate_otp()
            EmailOTP.objects.filter(email=email).delete()
            EmailOTP.objects.create(email=email, otp=otp)
            
            # Build an absolute URL for OTP verification
            verification_url = request.build_absolute_uri(reverse('verify_otp'))
            
            send_otp_email(email, otp, name, verification_url)
            request.session['pending_activation_user_id'] = user.user_id

            messages.success(request, 'Please check your email for the OTP verification code.')
            return redirect('verify_otp')
    else:
        form = RegisterForm()
    return render(request, 'user_querySafe/register.html', {'form': form})

@redirect_authenticated_user
def verify_otp_view(request):
    if 'pending_activation_user_id' not in request.session:
        return redirect('register')

    try:
        user = User.objects.get(user_id=request.session['pending_activation_user_id'])
    except User.DoesNotExist:
        return redirect('register')

    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp']

            try:
                email_otp = EmailOTP.objects.get(email=user.email, is_verified=False)
                if email_otp.is_valid():
                    if email_otp.otp == entered_otp:
                        # Update user status
                        user.registration_status = 'otp_verified'
                        user.otp_verified_at = timezone.now()
                        user.save()
                        
                        # Mark OTP as verified
                        email_otp.is_verified = True
                        email_otp.save()
                        
                        messages.success(request, 'Email verified successfully! Please activate your account.')
                        return redirect('verify_activation')
                    else:
                        messages.error(request, 'Invalid OTP. Please try again.')
                else:
                    messages.error(request, 'OTP has expired. Please request a new one.')
            except EmailOTP.DoesNotExist:
                messages.error(request, 'No valid OTP found. Please request a new one.')
    else:
        form = OTPVerificationForm()
    
    return render(request, 'user_querySafe/verify_otp.html', {'form': form, 'user': user})

@redirect_authenticated_user
def verify_activation_view(request):
    if 'pending_activation_user_id' not in request.session:
        return redirect('login')

    if request.method == 'POST':
        activation_code = request.POST.get('activation_code')
        try:
            code = ActivationCode.objects.get(code=activation_code)
            if code.times_used < 5:
                user = User.objects.get(user_id=request.session['pending_activation_user_id'])
                
                # Update user status
                user.is_active = True
                user.registration_status = 'activated'
                user.activated_at = timezone.now()
                user.save()
                
                # Increment usage counter
                code.times_used += 1
                code.save()
                
                # Set user session
                request.session['user_id'] = user.user_id
                
                # Build dashboard URL
                dashboard_url = request.build_absolute_uri(reverse('dashboard'))
                
                # Send welcome email with dynamic values
                send_welcome_email(user.email, user.name, dashboard_url)
                
                # Clear activation session
                del request.session['pending_activation_user_id']
                
                messages.success(request, 'Account activated successfully! Welcome to QuerySafe.')
                return redirect('dashboard')
            else:
                messages.error(request, 'This activation code has reached its usage limit.')
        except ActivationCode.DoesNotExist:
            messages.error(request, 'Invalid activation code.')
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('login')
    return render(request, 'user_querySafe/verify_account_activate.html')

def index_view(request):
    return render(request, 'user_querySafe/index.html')

@redirect_authenticated_user
def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            try:
                user = User.objects.get(email=email)
                if user.password == password:
                    # Check registration status and activate process if needed
                    if user.registration_status == 'registered':
                        request.session['pending_activation_user_id'] = user.user_id
                        messages.info(request, 'Please verify your email first.')
                        return redirect('verify_otp')
                    elif user.registration_status == 'otp_verified':
                        request.session['pending_activation_user_id'] = user.user_id
                        messages.info(request, 'Please activate your account.')
                        return redirect('verify_activation')
                    elif not user.is_active:
                        request.session['pending_activation_user_id'] = user.user_id
                        messages.info(request, 'Please activate your account.')
                        return redirect('verify_activation')
                    
                    # Successful login, store user_id in session
                    request.session['user_id'] = user.user_id

                    # Check for active user plan and store in session
                    active_plan = UserPlanAlot.objects.filter(
                        user=user,
                        expire_date__gte=timezone.now()
                    ).order_by('-timestamp').first()
                    request.session['active_plan'] = active_plan.plan_name if active_plan else "No active plan"
                    
                    messages.success(request, f'Welcome back, {user.name}!')
                    return redirect('dashboard')
                else:
                    messages.error(request, 'Invalid password')
            except User.DoesNotExist:
                messages.error(request, 'No account found with this email')
    else:
        form = LoginForm()
    
    return render(request, 'user_querySafe/login.html', {'form': form})

@login_required
def dashboard_view(request):
    user = User.objects.get(user_id=request.session['user_id'])
    
    # Get user's chatbots
    chatbots = Chatbot.objects.filter(user=user)
    
    # Calculate metrics
    total_chatbots = chatbots.count()
    trained_chatbots = chatbots.filter(status='trained').count()
    
    # Get conversations data
    total_conversations = Conversation.objects.filter(chatbot__in=chatbots).count()
    last_24h = timezone.now() - timedelta(days=1)
    recent_conversations = Conversation.objects.filter(
        chatbot__in=chatbots,
        started_at__gte=last_24h  # Changed from created_at to started_at
    ).count()
    
    # Get documents data
    total_documents = ChatbotDocument.objects.filter(chatbot__in=chatbots).count()
    trained_documents = ChatbotDocument.objects.filter(
        chatbot__in=chatbots.filter(status='trained')
    ).count()
    
    # Get messages data
    total_messages = Message.objects.filter(conversation__chatbot__in=chatbots).count()
    avg_response_time = 500  # Placeholder - implement actual calculation if needed
    
    # Get recent chatbots with their stats
    recent_chatbots = chatbots.annotate(
        total_messages=Count('conversations__messages')
    ).order_by('-id')[:5]  # Changed from created_at to id for ordering
    
    context = {
        'user': user,
        'total_chatbots': total_chatbots,
        'trained_chatbots': trained_chatbots,
        'total_conversations': total_conversations,
        'recent_conversations': recent_conversations,
        'total_documents': total_documents,
        'trained_documents': trained_documents,
        'total_messages': total_messages,
        'avg_response_time': avg_response_time,
        'recent_chatbots': recent_chatbots,
    }
    
    return render(request, 'user_querySafe/dashboard.html', context)

@login_required
def my_chatbots(request):
    user = User.objects.get(user_id=request.session['user_id'])
    chatbots = Chatbot.objects.filter(user=user).prefetch_related('conversations')
    
    # Get active plan and usage data
    active_plan = UserPlanAlot.objects.filter(
        user=user,
        expire_date__gte=timezone.now().date()
    ).order_by('-timestamp').first()
    
    current_chatbots = chatbots.count()
    
    context = {
        'chatbots': chatbots,
        'active_plan': active_plan,
        'chatbots_used': current_chatbots,
        'chatbots_total': active_plan.no_of_bot if active_plan else 0,
        'chatbots_remaining': (active_plan.no_of_bot - current_chatbots) if active_plan else 0
    }
    
    return render(request, 'user_querySafe/my_chatbots.html', context)

def logout_view(request):
    if 'user_id' in request.session:
        del request.session['user_id']
        messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

@login_required
def create_chatbot(request):
    user = User.objects.get(user_id=request.session['user_id'])
    
    # Get current active plan from UserPlanAlot
    active_plan = UserPlanAlot.objects.filter(
        user=user,
        expire_date__gte=timezone.now().date()
    ).order_by('-timestamp').first()  # Get the most recent active plan
    
    # Check if user has an active plan
    if not active_plan:
        context = {
            'alert': {
                'type': 'danger',
                'message': 'You do not have an active subscription to create chatbots.',
                'link': {
                    'text': 'Subscribe to a plan',
                    'url': 'subscriptions'
                }
            }
        }
        return render(request, 'user_querySafe/create_chatbot.html', context)
    
    # Get current number of chatbots
    current_chatbots = Chatbot.objects.filter(
        user=user,
        created_at__gte=active_plan.start_date,
        created_at__lte=active_plan.expire_date
    ).count()
    
    # Check if user has reached their chatbot limit
    if current_chatbots >= active_plan.no_of_bot:
        context = {
            'alert': {
                'type': 'warning',
                'message': f'You have reached your limit of {active_plan.no_of_bot} chatbots under the {active_plan.plan_name} plan.',
                'link': {
                    'text': 'Contact us to upgrade',
                    'url': 'contact'
                }
            }
        }
        return render(request, 'user_querySafe/create_chatbot.html', context)

    if request.method == 'POST':
        form = ChatbotCreateForm(request.POST, request.FILES)
        if form.is_valid():
            chatbot = form.save(commit=False)
            chatbot.user = user
            chatbot.save()
            
            # Create activity record
            Activity.objects.create(
                user=user,
                activity_type='create_chatbot',
                description=f'Created new chatbot: {chatbot.name}'
            )
            
            messages.success(request, 'Chatbot created successfully!')
            return redirect('my_chatbots')
    else:
        form = ChatbotCreateForm()
    
    # Add context for the template
    context = {
        'form': form,
        'active_plan': active_plan,
        'chatbots_used': current_chatbots,
        'chatbots_total': active_plan.no_of_bot,
        'chatbots_remaining': active_plan.no_of_bot - current_chatbots,
        'plan_expires': active_plan.expire_date.strftime('%B %d, %Y')
    }
    
    return render(request, 'user_querySafe/create_chatbot.html', context)

@login_required
def conversations_view(request, chatbot_id=None, conversation_id=None):
    user = User.objects.get(user_id=request.session['user_id'])
    chatbots = Chatbot.objects.filter(user=user)
    
    selected_bot = None
    conversations = []
    selected_conversation = None
    messages = []
    
    if chatbot_id:
        selected_bot = get_object_or_404(Chatbot, chatbot_id=chatbot_id, user=user)
        conversations = Conversation.objects.filter(chatbot=selected_bot).order_by('-last_updated')
        
        # Add last message to each conversation
        for conv in conversations:
            last_msg = Message.objects.filter(conversation=conv).last()
            conv.last_message = last_msg.content if last_msg else ""
            conv.unread_count = Message.objects.filter(
                conversation=conv, 
                is_bot=True, 
                timestamp__gt=conv.last_updated
            ).count()
        
        if conversation_id:
            selected_conversation = get_object_or_404(Conversation, conversation_id=conversation_id, chatbot=selected_bot)
            messages = Message.objects.filter(conversation=selected_conversation).order_by('timestamp')
        elif conversations.exists():
            selected_conversation = conversations.first()
            messages = Message.objects.filter(conversation=selected_conversation).order_by('timestamp')
    
    context = {
        'chatbots': chatbots,
        'selected_bot': selected_bot,
        'conversations': conversations,
        'selected_conversation': selected_conversation,
        'messages': messages,
    }
    
    return render(request, 'user_querySafe/conversations.html', context)

def chatbot_view(request, chatbot_id):
    # Get the chatbot or return 404
    chatbot = get_object_or_404(Chatbot, chatbot_id=chatbot_id)
    
    # Only allow access if chatbot is trained
    if chatbot.status != 'trained':
        messages.error(request, 'This chatbot is not ready yet.')
        return redirect('my_chatbots')
    
    context = {
        'chatbot': chatbot,
        'chatbot_name': chatbot.name,
        'chatbot_logo': chatbot.logo.url if chatbot.logo else None,
        'chatbot_id': chatbot.chatbot_id,
    }
    
    return render(request, 'user_querySafe/chatbot-view.html', context)

def chatbot_status(request):
    if 'user_id' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    user = User.objects.get(user_id=request.session['user_id'])
    chatbots = Chatbot.objects.filter(user=user)
    data = [{'chatbot_id': bot.chatbot_id, 'status': bot.status} for bot in chatbots]
    return JsonResponse(data, safe=False)

@csrf_exempt
def chat_message(request):
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = HttpResponse()
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        response['Access-Control-Max-Age'] = '86400'  # 24 hours
        return response

    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        user_message = data.get('query', '')
        chatbot_id = data.get('chatbot_id')
        conversation_id = data.get('conversation_id')
        
        # Ensure we have a session
        if not request.session.session_key:
            request.session.create()
        session_id = request.session.session_key
        
        # Get chatbot
        chatbot = get_object_or_404(Chatbot, chatbot_id=chatbot_id)
        
        # Get or create conversation
        try:
            if conversation_id:
                conversation = Conversation.objects.get(conversation_id=conversation_id)
            else:
                conversation = Conversation.objects.create(
                    chatbot=chatbot,
                    user_id=session_id
                )
                print(f"Created new conversation: {conversation.conversation_id}")
        except Conversation.DoesNotExist:
            conversation = Conversation.objects.create(
                chatbot=chatbot,
                user_id=session_id
            )
            print(f"Created new conversation: {conversation.conversation_id}")

        # Store user message
        Message.objects.create(
            conversation=conversation,
            content=user_message,
            is_bot=False
        )
        print(f"Stored user message in conversation: {conversation.conversation_id}")

        # Get chat history (last 5 messages)
        chat_history = Message.objects.filter(conversation=conversation).order_by('-timestamp')[:5]
        chat_context = "\n".join([
            f"{'Bot' if msg.is_bot else 'User'}: {msg.content}"
            for msg in reversed(chat_history)
        ])
        
        # Get vector search results
        index_path = os.path.join(settings.INDEX_DIR, f"{chatbot_id}-index.index")
        meta_path = os.path.join(settings.META_DIR, f"{chatbot_id}-chunks.json")
        
        if not os.path.exists(index_path) or not os.path.exists(meta_path):
            return JsonResponse({'error': 'Chatbot data not found'}, status=404)
        
        index = faiss.read_index(index_path)
        with open(meta_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        
        query_vector = embedding_model.encode([user_message]).astype('float32')
        k = 5
        distances, indices = index.search(query_vector, k)
        
        matches = []
        for i, idx in enumerate(indices[0]):
            if idx < len(chunks):
                matches.append({
                    'content': chunks[idx],
                    'distance': float(distances[0][i])
                })
        
        knowledge_context = "\n\n".join([m['content'] for m in matches])
        
        # Build prompt with both chat history and knowledge context
        prompt = f"""Previous conversation:
{chat_context}

Knowledge context:
{knowledge_context}

Based on the conversation history and available knowledge, provide a natural and contextually appropriate response to:
{user_message}

Remember to:
1. Maintain conversation continuity
2. Reference previous context when relevant
3. Be natural and conversational
4. Only use knowledge context if relevant to the current query
5. Avoid unnecessary repetition.
6. If the user asks for a specific document, provide a summary or key points from that document.
7. Do not say any words like "based on context or documents" just show like you know about this and you are answering the user.
8. 
"""
        
        # Get response from Gemini
        gemini_response = client.models.generate_content(
            model="gemini-2.0-flash-001",
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        
        bot_response = gemini_response.text
        
        # Store bot response
        Message.objects.create(
            conversation=conversation,
            content=bot_response,
            is_bot=True
        )
        print(f"Stored bot response in conversation: {conversation.conversation_id}")

        # Update conversation last_updated
        conversation.save()
        
        response = JsonResponse({
            'answer': bot_response,
            'conversation_id': conversation.conversation_id,
            'matches': matches
        })
        
        # Add CORS headers to the response
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        
        return response
        
    except Exception as e:
        response = JsonResponse({'error': str(e)}, status=400)
        response['Access-Control-Allow-Origin'] = '*'
        return response

@xframe_options_exempt
@csrf_exempt
def serve_widget_js(request, chatbot_id):
    if request.method == 'OPTIONS':
        response = HttpResponse()
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    chatbot = get_object_or_404(Chatbot, chatbot_id=chatbot_id)
    
    # Get absolute URLs
    base_url = request.build_absolute_uri('/').rstrip('/')
    logo_url = request.build_absolute_uri(chatbot.logo.url) if chatbot.logo else None
    
    context = {
        'chatbot': chatbot,
        'chatbot_name': chatbot.name,
        'chatbot_logo': logo_url,
        'base_url': base_url,
    }
    
    response = render(request, 'user_querySafe/widget.js', context, content_type='application/javascript')
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

def get_widget_code(chatbot_id, base_url):
    return f"""<!-- querySafe Chatbot Widget -->
<script>
(function(w,d,s,id){{
    var js, fjs = d.getElementsByTagName(s)[0];
    if (d.getElementById(id)){{return;}}
    js = d.createElement(s);
    js.id = id;
    js.src = "{base_url}/widget/{chatbot_id}/querySafe.js";
    js.async = true;
    fjs.parentNode.insertBefore(js, fjs);
}}(window, document, 'script', 'querySafe-widget'));
</script>"""

def get_widget_snippet(request, chatbot_id):
    if request.method != 'GET':
        return JsonResponse({'error': 'Only GET method allowed'}, status=405)
    
    chatbot = get_object_or_404(Chatbot, chatbot_id=chatbot_id)
    base_url = request.build_absolute_uri('/').rstrip('/')
    
    snippet = get_widget_code(chatbot_id, base_url)
    return JsonResponse({'snippet': snippet})

def chatbot_detail_view(request, pk):
    if 'user_id' not in request.session:
        return redirect('login')
    
    user = User.objects.get(user_id=request.session['user_id'])
    chatbot = get_object_or_404(Chatbot, id=pk, user=user)
    
    context = {
        'chatbot': chatbot,
        # Add other context data as needed
    }
    return render(request, 'user_querySafe/chatbot_detail.html', context)

@login_required
def profile_view(request):
    user = User.objects.get(user_id=request.session['user_id'])
    
    # Get active plan
    active_plan = UserPlanAlot.objects.filter(
        user=user,
        expire_date__gte=timezone.now().date()
    ).order_by('-timestamp').first()
    
    # Get statistics
    stats = {
        'total_chatbots': Chatbot.objects.filter(user=user).count(),
        'total_conversations': Conversation.objects.filter(chatbot__user=user).count(),
        'total_messages': Message.objects.filter(conversation__chatbot__user=user).count(),
        'total_documents': ChatbotDocument.objects.filter(chatbot__user=user).count(),
    }
    
    # Get recent activities (last 10)
    recent_activities = Activity.objects.filter(user=user).order_by('-timestamp')[:10]
    
    context = {
        'user': user,
        'active_plan': active_plan,
        **stats,
        'recent_activities': recent_activities
    }
    
    return render(request, 'user_querySafe/profile.html', context)

@require_POST
def update_profile(request):
    user = User.objects.get(user_id=request.session['user_id'])
    
    # Update basic info
    user.name = request.POST.get('name', user.name)
    user.email = request.POST.get('email', user.email)
    
    # Handle profile image upload
    if 'profile_image' in request.FILES:
        user.profile_image = request.FILES['profile_image']
    
    user.save()
    
    messages.success(request, 'Profile updated successfully!')
    return redirect('profile')

@require_http_methods(["POST"])
@csrf_exempt
def resend_otp_view(request):
    if request.method == 'POST':
        try:
            if 'pending_activation_user_id' not in request.session:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid session. Please register again.'
                })

            user = User.objects.get(user_id=request.session['pending_activation_user_id'])
            
            # Add rate limiting using cache
            cache_key = f'resend_otp_{user.email}'
            if cache.get(cache_key):
                return JsonResponse({
                    'success': False,
                    'message': 'Please wait before requesting another OTP.'
                })
            
            # Set cache to prevent duplicate requests
            cache.set(cache_key, True, 30)  # 30 seconds cooldown
            
            # Generate new OTP
            otp = generate_otp()
            
            # Delete any existing OTP
            EmailOTP.objects.filter(email=user.email).delete()
            
            # Create new OTP
            EmailOTP.objects.create(email=user.email, otp=otp)
            
            # Send OTP email
            if send_otp_email(user.email, otp):
                return JsonResponse({
                    'success': True,
                    'message': 'OTP sent successfully!'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Failed to send OTP. Please try again.'
                })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'User not found. Please register again.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

def contact_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone', '')
        message = request.POST.get('message')

        try:
            # Save the contact form data to the database
            contact = Contact.objects.create(
                name=name,
                email=email,
                phone=phone,
                message=message
            )

            # Send email notification to admin
            subject = f"New Contact Form Submission from {name}"
            html_message = render_to_string('user_querySafe/email/contact-submission.html', {
                'name': name,
                'email': email,
                'phone': phone,
                'message': message,
                'project_name': settings.PROJECT_NAME,
            })
            plain_message = f"""
You have received a new contact form submission:

Name: {name}
Email: {email}
Phone: {phone}
Message:
{message}
"""
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],
                html_message=html_message,
                fail_silently=False,
            )

            # Success message
            messages.success(request, 'Thank you for contacting us! We will get back to you soon.')
        except Exception as e:
            print(f"Error: {e}")
            messages.error(request, 'There was an error submitting the form. Please try again.')

        return redirect('contact')

    return render(request, 'user_querySafe/contact-us.html')

@login_required
def subscription_view(request):
    public_plans = SubscriptionPlan.objects.filter(status='public').order_by('pricing')
    print("Plans:", [(plan.plan_id, plan.plan_name) for plan in public_plans])  # Changed from id to plan_id
    return render(request, 'user_querySafe/subscriptions.html', {'public_plans': public_plans})

@login_required
def plan_activation_view(request, plan_id):
    user = User.objects.get(user_id=request.session['user_id'])
    plan = get_object_or_404(SubscriptionPlan, plan_id=plan_id, status='public')
    
    if request.method == 'POST':
        if plan.pricing == 0:
            activation_code = request.POST.get('activation_code')
            try:
                code = ActivationCode.objects.get(code=activation_code)
                if code.times_used < 10:  # Using fixed value 10 instead of max_uses
                    # Calculate dates
                    start_date = timezone.now().date()
                    expire_date = start_date + timedelta(days=30)  # 30 days from now
                    
                    # Create UserPlanAlot instance with plan details
                    UserPlanAlot.objects.create(
                        user=user,
                        plan_name=plan.plan_name,
                        start_date=start_date,
                        no_of_bot=plan.no_of_bot,
                        no_query=plan.no_query_per_bot,
                        no_of_docs=plan.no_of_docs_per_bot,
                        doc_size_limit=plan.size_limit_per_docs,
                        expire_date=expire_date
                    )
                    
                    # Update activation code usage
                    code.times_used += 1
                    code.save()
                    
                    # Update session with new plan
                    request.session['active_plan'] = plan.plan_name
                    
                    messages.success(request, f'{plan.plan_name} activated successfully!')
                    return redirect('dashboard')
                else:
                    messages.error(request, 'This activation code has reached its usage limit.')
            except ActivationCode.DoesNotExist:
                messages.error(request, 'Invalid activation code.')
        else:
            # Handle paid plans (implement payment gateway integration)
            messages.info(request, 'Payment gateway integration coming soon!')
            return redirect('subscriptions')
    
    return render(request, 'user_querySafe/plan-activation.html', {'plan': plan})

@login_required
def usage_view(request):
    user = User.objects.get(user_id=request.session['user_id'])
    
    # Get active plan
    active_plan = UserPlanAlot.objects.filter(
        user=user,
        expire_date__gte=timezone.now().date()
    ).order_by('-timestamp').first()

    # Get user's chatbots
    chatbots = Chatbot.objects.filter(user=user)
    
    # Calculate totals
    total_chatbots = chatbots.count()
    total_messages = Message.objects.filter(conversation__chatbot__in=chatbots).count()
    total_documents = ChatbotDocument.objects.filter(chatbot__in=chatbots).count()

    # Calculate percentages
    if active_plan:
        chatbot_percentage = min(100, (total_chatbots / active_plan.no_of_bot * 100) if active_plan.no_of_bot > 0 else 0)
        message_percentage = min(100, (total_messages / active_plan.no_query * 100) if active_plan.no_query > 0 else 0)
        document_percentage = min(100, (total_documents / active_plan.no_of_docs * 100) if active_plan.no_of_docs > 0 else 0)
    else:
        chatbot_percentage = message_percentage = document_percentage = 0
    
    context = {
        'user': user,
        'active_plan': active_plan,
        'total_chatbots': total_chatbots,
        'total_messages': total_messages,
        'total_documents': total_documents,
        'chatbot_percentage': chatbot_percentage,
        'message_percentage': message_percentage,
        'document_percentage': document_percentage,
        'recent_activities': Activity.objects.filter(user=user).order_by('-timestamp')[:10]
    }
    
    return render(request, 'user_querySafe/usage.html', context)

@login_required
def mail_templates_view(request):
    return render(request, 'user_querySafe/email/email-templates.html')