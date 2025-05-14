from django.urls import path
from . import views

urlpatterns = [
    # subscriptions related path
    path('subscriptions/', views.subscription_view, name='subscriptions'),
    path('plan-activation/<str:plan_id>/', views.plan_activation_view, name='plan_activation'),
    path('usage/', views.usage_view, name='usage'),
]