from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # dashboard_paths
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('', views.index_view, name='index'),


    # my custom modules
    path('chatbot/', include('user_querySafe.chatbot.urls')),


    # authentication related path
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('resend-otp/', views.resend_otp_view, name='resend_otp'),
    path('verify-activation/', views.verify_activation_view, name='verify_activation'),

    # conversations related paths
    path('conversations/', views.conversations_view, name='conversations'),
    path('conversations/<str:chatbot_id>/', views.conversations_view, name='conversations_by_chatbot'),
    path('conversations/<str:chatbot_id>/<str:conversation_id>/', views.conversations_view, name='conversation_detail'),

    # Chatbot widget related paths
    path('chatbot_view/<str:chatbot_id>/', views.chatbot_view, name='chatbot_view'),
    path('chat/', views.chat_message, name='chat_message'),
    path('widget/<str:chatbot_id>/querySafe.js', views.serve_widget_js, name='widget_js'),

    # profile related paths
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),

    # contact related path
    path('contact/', views.contact_view, name='contact'),

    # subscriptions related path
    path('plan/', include('user_querySafe.subscription.urls'), name='plan'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)