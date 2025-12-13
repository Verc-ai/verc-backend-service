"""
Serializers for analytics data validation and transformation.
"""
from rest_framework import serializers


class ScorecardResponseSerializer(serializers.Serializer):
    """Serializer for scorecard API response."""
    period = serializers.CharField()
    metrics = serializers.DictField()
    trends = serializers.DictField(required=False)


class TrendsResponseSerializer(serializers.Serializer):
    """Serializer for trends API response."""
    period = serializers.CharField()
    metrics = serializers.DictField()


class HealthResponseSerializer(serializers.Serializer):
    """Serializer for health metrics API response."""
    period = serializers.CharField()
    metrics = serializers.DictField()

