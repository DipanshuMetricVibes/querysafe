from pyexpat.errors import messages
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from user_querySafe.decorators import login_required
from user_querySafe.forms import ChatbotCreateForm
from user_querySafe.models import Activity, Chatbot, ChatbotDocument, User, UserPlanAlot
from user_querySafe.vectorization.pipeline_processor import run_pipeline_background

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


@login_required
def create_chatbot(request):
    user = User.objects.get(user_id=request.session['user_id'])
    
    # Get current active plan from UserPlanAlot
    active_plan = UserPlanAlot.objects.filter(
        user=user,
        expire_date__gte=timezone.now().date()
    ).order_by('-timestamp').first()  # Most recent active plan
    
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
    
    # Get current number of chatbots within plan duration
    current_chatbots = Chatbot.objects.filter(
        user=user,
        created_at__gte=active_plan.start_date,
        created_at__lte=active_plan.expire_date
    ).count()
    
    # Check if user reached chatbot limit
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
                title='Chatbot Creation',
                description=f'Created new chatbot: {chatbot.name}',
                type='success'  # Allowed values: 'primary', 'success', 'info', 'warning'
            )
            
            # Process document uploads
            uploaded_docs = request.FILES.getlist('pdf_files')
            print("DEBUG: Number of documents uploaded:", len(uploaded_docs))
            if uploaded_docs:
                for doc in uploaded_docs:
                    ChatbotDocument.objects.create(
                        chatbot=chatbot,
                        document=doc  # use correct field name as defined in your model
                    )
            else:
                print("DEBUG: No files found in request.FILES under 'pdf_files'")
            
            # Run the processing pipeline in background (will process uploaded documents)
            run_pipeline_background(chatbot.chatbot_id)
            
            messages.success(request, 'Chatbot created successfully!')
            return redirect('my_chatbots')
    else:
        form = ChatbotCreateForm()
    
    # Context for template
    context = {
        'form': form,
        'active_plan': active_plan,
        'chatbots_used': current_chatbots,
        'chatbots_total': active_plan.no_of_bot,
        'chatbots_remaining': active_plan.no_of_bot - current_chatbots,
        'plan_expires': active_plan.expire_date.strftime('%B %d, %Y')
    }
    
    return render(request, 'user_querySafe/create_chatbot.html', context)

def chatbot_status(request):
    if 'user_id' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    user = User.objects.get(user_id=request.session['user_id'])
    chatbots = Chatbot.objects.filter(user=user)
    data = [{'chatbot_id': bot.chatbot_id, 'status': bot.status} for bot in chatbots]
    return JsonResponse(data, safe=False)

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
