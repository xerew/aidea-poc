from rest_framework import serializers

from hub.models import UserProfile

_VALID_PILLARS = ['teach-with-ai', 'teach-for-ai', 'teach-about-ai']
_VALID_STYLES  = [c[0] for c in UserProfile.LearningStyle.choices]


class ProfilePreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model  = UserProfile
        fields = ['preferred_pillars', 'learning_style']

    def validate_preferred_pillars(self, value):
        for pillar in value:
            if pillar not in _VALID_PILLARS:
                raise serializers.ValidationError(
                    f"'{pillar}' is not a valid pillar. Choose from {_VALID_PILLARS}."
                )
        return value

    def validate_learning_style(self, value):
        if value and value not in _VALID_STYLES:
            raise serializers.ValidationError(
                f"'{value}' is not a valid learning style. Choose from {_VALID_STYLES}."
            )
        return value
