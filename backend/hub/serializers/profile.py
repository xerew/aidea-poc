from rest_framework import serializers

from hub.models import UserProfile

_VALID_PILLARS = ['teach-with-ai', 'teach-for-ai', 'teach-about-ai']
_VALID_STYLES  = [c[0] for c in UserProfile.LearningStyle.choices]


class ProfilePreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model  = UserProfile
        fields = [
            'preferred_pillars', 'learning_style',
            'weekly_learning_goal', 'email_notifications', 'progress_reminders',
        ]

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


class ProfilePersonalInfoSerializer(serializers.Serializer):
    first_name   = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name    = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email        = serializers.EmailField(required=False)
    subject_area = serializers.ChoiceField(
        choices=[('', '')] + list(UserProfile.SubjectArea.choices),
        required=False, allow_blank=True,
    )
    gender  = serializers.ChoiceField(
        choices=[('', '')] + list(UserProfile.Gender.choices),
        required=False, allow_blank=True,
    )
    country  = serializers.CharField(max_length=2,   required=False, allow_blank=True)
    school   = serializers.CharField(max_length=200, required=False, allow_blank=True)
    phone    = serializers.CharField(max_length=30,  required=False, allow_blank=True)
    location = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def to_representation(self, instance):
        user = instance.user
        return {
            'first_name':   user.first_name,
            'last_name':    user.last_name,
            'email':        user.email,
            'subject_area': instance.subject_area,
            'gender':       instance.gender,
            'country':      instance.country,
            'school':       instance.school,
            'phone':        instance.phone,
            'location':     instance.location,
        }

    def update(self, instance, validated_data):
        user = instance.user
        user.first_name = validated_data.get('first_name', user.first_name)
        user.last_name  = validated_data.get('last_name',  user.last_name)
        user.email      = validated_data.get('email',      user.email)
        user.save(update_fields=['first_name', 'last_name', 'email'])

        instance.subject_area = validated_data.get('subject_area', instance.subject_area)
        instance.gender       = validated_data.get('gender',       instance.gender)
        instance.country      = validated_data.get('country',      instance.country)
        instance.school       = validated_data.get('school',       instance.school)
        instance.phone        = validated_data.get('phone',        instance.phone)
        instance.location     = validated_data.get('location',     instance.location)
        instance.save(update_fields=['subject_area', 'gender', 'country', 'school', 'phone', 'location'])
        return instance


class ProfileSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model  = UserProfile
        fields = ['profile_public', 'share_progress']
