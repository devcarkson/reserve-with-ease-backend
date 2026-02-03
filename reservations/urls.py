from django.urls import path
from . import views

app_name = 'reservations'

urlpatterns = [
    path('', views.ReservationListCreateView.as_view(), name='reservation-list-create'),
    path('create/', views.create_reservation_view, name='create-reservation'),
    path('owner/', views.owner_reservations_view, name='owner-reservations'),
    path('stats/', views.reservation_stats_view, name='reservation-stats'),
    path('calendar/', views.reservation_calendar_view, name='reservation-calendar'),
    path('<int:pk>/', views.ReservationDetailView.as_view(), name='reservation-detail'),
    path('<int:reservation_id>/cancel/', views.cancel_reservation_view, name='cancel-reservation'),
    path('<int:reservation_id>/confirm/', views.confirm_reservation_view, name='confirm-reservation'),
    path('<int:reservation_id>/check-in/', views.check_in_reservation_view, name='check-in-reservation'),
    path('<int:reservation_id>/check-out/', views.check_out_reservation_view, name='check-out-reservation'),
    path('<int:reservation_id>/payment/', views.add_payment_view, name='add-payment'),
    path('<str:reservation_ref>/upload-receipt/', views.upload_payment_receipt_view, name='upload-receipt'),
    path('<int:reservation_id>/approve-payment/', views.approve_payment_view, name='approve-payment'),
    path('check-availability/', views.check_availability_view, name='check-availability'),
    path('performance-stats/', views.performance_stats_view, name='performance-stats'),
]
