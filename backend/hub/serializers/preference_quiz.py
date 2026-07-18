from rest_framework import serializers

from hub.models import PreferenceOption, PreferenceQuestion


class PreferenceOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PreferenceOption
        fields = ['id', 'text']  # maps_to deliberately hidden


class PreferenceQuestionSerializer(serializers.ModelSerializer):
    options = PreferenceOptionSerializer(many=True, read_only=True)

    class Meta:
        model  = PreferenceQuestion
        fields = ['id', 'text', 'options']
