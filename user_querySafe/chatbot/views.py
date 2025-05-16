import json  # Add this import at the top
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from user_querySafe.decorators import login_required
from user_querySafe.forms import ChatbotCreateForm
from user_querySafe.models import Activity, Chatbot, ChatbotDocument, User, UserPlanAlot
from .pipeline_processor import run_pipeline_background


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
        'chatbots_remaining': (active_plan.no_of_bot - current_chatbots) if active_plan else 0,
        'show_toaster': False,
    }    
    return render(request, 'user_querySafe/my_chatbots.html', context)

@login_required
def create_chatbot(request):
    user = User.objects.get(user_id=request.session['user_id'])

    # Get the current active plan
    active_plan = UserPlanAlot.objects.filter(
        user=user,
        expire_date__gte=timezone.now().date()
    ).order_by('-timestamp').first()

    if not active_plan:
        messages.error(request, "You do not have an active subscription to create chatbots.")
        return redirect('my_chatbots')

    # Check if user reached chatbot limit
    current_chatbots = Chatbot.objects.filter(user=user).count()
    if current_chatbots >= active_plan.no_of_bot:
        messages.warning(
            request,
            f"You have reached your limit of {active_plan.no_of_bot} chatbots under the {active_plan.plan_name} plan. "
            f"<a href='{reverse('contact')}' class='alert-link'>Contact us to upgrade</a>."
        )
        return redirect('my_chatbots')

    if request.method == 'POST':
        form = ChatbotCreateForm(request.POST, request.FILES)
        if form.is_valid():
            chatbot = form.save(commit=False)
            chatbot.user = user
            chatbot.save()

            # Process document uploads
            uploaded_docs = request.FILES.getlist('pdf_files')
            allowed_docs = active_plan.no_of_docs
            allowed_size_bytes = active_plan.doc_size_limit * 1024 * 1024

            if len(uploaded_docs) > allowed_docs:
                messages.error(request, f"You can upload a maximum of {allowed_docs} file(s) as per your subscription.")
                return redirect('create_chatbot')

            successful_uploads = 0
            for doc in uploaded_docs:
                if doc.size > allowed_size_bytes:
                    messages.error(request, f"File '{doc.name}' exceeds the size limit of {active_plan.doc_size_limit} MB.")
                    continue

                ChatbotDocument.objects.create(chatbot=chatbot, document=doc)
                successful_uploads += 1

            if successful_uploads > 0:
                messages.success(request, f"Chatbot '{chatbot.name}' created successfully with {successful_uploads} document(s)!")
                return redirect('my_chatbots')
            else:
                messages.error(request, "No documents were uploaded successfully.")
                chatbot.delete()
                return redirect('create_chatbot')
    else:
        form = ChatbotCreateForm()

    context = {
        'form': form,
        'active_plan': active_plan,
    }
    return render(request, 'user_querySafe/create_chatbot.html', context)

@login_required
def change_chatbot_status(request):
    """
    AJAX view to change the status of a chatbot.
    Expects JSON with keys "chatbot_id" and "new_status".
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            chatbot_id = data.get('chatbot_id')
            new_status = data.get('new_status')
            
            # Add user verification
            user = User.objects.get(user_id=request.session['user_id'])
            chatbot = get_object_or_404(Chatbot, chatbot_id=chatbot_id, user=user)
            
            # Update status
            chatbot.status = new_status
            chatbot.save()
            
            # Log the activity
            Activity.objects.create(
                user=user,
                title='Chatbot Status Change',
                description=f'Changed chatbot {chatbot.name} status to {new_status}',
                type='info'
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Chatbot status changed to {new_status}'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': str(e)
            }, status=400)
            
    return JsonResponse({
        'error': 'Invalid request method'
    }, status=405)

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
