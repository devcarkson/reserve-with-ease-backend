from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    path('', views.PropertySearchView.as_view(), name='property-search'),
    path('queries/', views.SearchQueryListView.as_view(), name='search-queries'),
    path('popular/', views.PopularSearchListView.as_view(), name='popular-searches'),
    path('saved/', views.SavedSearchListView.as_view(), name='saved-searches'),
    path('suggestions/', views.search_suggestions_view, name='search-suggestions'),
    path('trending/', views.trending_searches_view, name='trending-searches'),
    path('location-trends/', views.location_trends_view, name='location-trends'),
    path('track/', views.track_search_view, name='track-search'),
    path('save/', views.save_search_view, name='save-search'),
]
