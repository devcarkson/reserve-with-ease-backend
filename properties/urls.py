from django.urls import path
from . import views

app_name = 'properties'

urlpatterns = [
    path('', views.PropertyListCreateView.as_view(), name='property-list-create'),
    path('search/', views.property_search_view, name='property-search'),
    path('my-properties/', views.my_properties_view, name='my-properties'),
    path('<int:pk>/', views.PropertyDetailView.as_view(), name='property-detail'),
    path('<int:property_id>/rooms/', views.RoomListCreateView.as_view(), name='room-list-create'),
    path('rooms/<int:pk>/', views.RoomDetailView.as_view(), name='room-detail'),
    path('<int:property_id>/room-categories/', views.RoomCategoryListCreateView.as_view(), name='room-category-list-create'),
    path('room-categories/<int:pk>/', views.RoomCategoryDetailView.as_view(), name='room-category-detail'),
    path('<int:property_id>/availability/', views.property_availability_view, name='property-availability'),
    path('<int:property_id>/calendar/', views.property_calendar_view, name='property-calendar'),
    path('<int:property_id>/availability/update/', views.update_property_availability_view, name='update-property-availability'),
    path('rooms/<int:room_id>/availability/', views.room_availability_view, name='room-availability'),
    path('<int:property_id>/upload-image/', views.upload_property_image_view, name='upload-property-image'),
    path('rooms/<int:room_id>/upload-image/', views.upload_room_image_view, name='upload-room-image'),
]
