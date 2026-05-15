from rest_framework import serializers

from hub.models.recommendations import RecommendationEvent


class RecommendationEventSerializer(serializers.Serializer):
    course_id  = serializers.IntegerField()
    event_type = serializers.ChoiceField(choices=RecommendationEvent.EventType.choices)
    rank       = serializers.IntegerField(min_value=0, max_value=20)
    source     = serializers.ChoiceField(choices=['personal', 'cf'])
