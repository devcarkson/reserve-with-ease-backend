from rest_framework import serializers
from .models import (
    SearchQuery, SearchClick, PopularSearch, SavedSearch,
    SearchAnalytics, PropertySearchRanking, SearchSuggestion,
    SearchFilter, LocationTrend
)


class SearchQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchQuery
        fields = '__all__'


class SearchClickSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchClick
        fields = '__all__'


class PopularSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = PopularSearch
        fields = '__all__'


class SavedSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedSearch
        fields = '__all__'


class SearchAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchAnalytics
        fields = '__all__'


class PropertySearchRankingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertySearchRanking
        fields = '__all__'


class SearchSuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchSuggestion
        fields = '__all__'


class SearchFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchFilter
        fields = '__all__'


class LocationTrendSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationTrend
        fields = '__all__'