
from datetime import timedelta
from pyexpat.errors import messages
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from user_querySafe.decorators import login_required
from user_querySafe.models import ActivationCode, Activity, Chatbot, ChatbotDocument, Message, SubscriptionPlan, User, UserPlanAlot
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import send_mail

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
                    expire_date = start_date + timedelta(days=30)  # 30 days validity
                    
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
                    
                    
                    # Build dashboard URL
                    dashboard_url = request.build_absolute_uri(reverse('dashboard'))
                    
                    # Send plan activation email with dynamic values
                    send_plan_activation_email(user.email, user.name, plan, start_date, expire_date, dashboard_url)
                    
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


def send_plan_activation_email(email, name, plan, start_date, expire_date, dashboard_url):
    try:
        subject = "Plan Activated Successfully"
        context = {
            'name': name,
            # You can dynamically pass these values from the plan
            'plan_name': plan.plan_name,
            'plan_limits': f"{plan.no_of_bot} Bot(s), {plan.no_query_per_bot} Queries per Bot, {plan.no_of_docs_per_bot} Document(s)",
            'start_date': start_date.strftime('%B %d, %Y'),
            'expire_date': expire_date.strftime('%B %d, %Y'),
            'dashboard_url': dashboard_url,
            'project_name': settings.PROJECT_NAME
        }
        html_message = render_to_string("user_querySafe/email/plan-activate.html", context)
        plain_message = (
            f"Hello {name},\n\n"
            f"Your plan '{plan.plan_name}' has been activated successfully.\n"
            f"Plan Limits: {plan.no_of_bot} Bot(s), {plan.no_query_per_bot} Queries per Bot, {plan.no_of_docs_per_bot} Document(s)\n"
            f"Start Date: {start_date.strftime('%B %d, %Y')}\n"
            f"Valid Till: {expire_date.strftime('%B %d, %Y')}\n\n"
            f"Go to your dashboard: {dashboard_url}\n\n"
            "Thank you for subscribing to QuerySafe."
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
        print(f"Error sending plan activation email: {str(e)}")
        return False


@login_required
def subscription_view(request):
    public_plans = SubscriptionPlan.objects.filter(status='public').order_by('pricing')
    print("Plans:", [(plan.plan_id, plan.plan_name) for plan in public_plans])  # Changed from id to plan_id
    return render(request, 'user_querySafe/subscriptions.html', {'public_plans': public_plans})
