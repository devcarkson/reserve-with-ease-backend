from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'payment-methods', views.PaymentMethodViewSet, basename='payment-methods')

urlpatterns = [
    path('', include(router.urls)),
    path('owner-payment-method/<str:owner_id>/', views.get_owner_payment_method_view, name='owner-payment-method'),
]