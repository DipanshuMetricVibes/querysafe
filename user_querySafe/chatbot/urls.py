from django.urls import path
from . import views

urlpatterns = [
    path('my_chatbots', views.my_chatbots, name='my_chatbots'),
    path('create/', views.create_chatbot, name='create_chatbot'),
    path('chatbot_status/', views.chatbot_status, name='chatbot_status'),
    path('chatbot/<int:pk>/', views.chatbot_detail_view, name='chatbot_detail'),
]