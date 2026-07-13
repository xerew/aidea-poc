import re

from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from hub.models import UserProfile

_PASSWORD_RULES = [
    (lambda p: len(p) >= 8,                         'at least 8 characters'),
    (lambda p: len(p) <= 128,                        'no more than 128 characters'),
    (lambda p: bool(re.search(r'[A-Z]', p)),        'at least one uppercase letter'),
    (lambda p: bool(re.search(r'[a-z]', p)),        'at least one lowercase letter'),
    (lambda p: bool(re.search(r'\d', p)),            'at least one number'),
    (lambda p: bool(re.search(r'[^A-Za-z0-9]', p)), 'at least one special character'),
]


class RegisterSerializer(serializers.Serializer):
    first_name       = serializers.CharField(max_length=150)
    last_name        = serializers.CharField(max_length=150)
    username         = serializers.CharField(max_length=150)
    email            = serializers.EmailField()
    gender           = serializers.ChoiceField(
        choices=[('', '')] + list(UserProfile.Gender.choices),
        required=False, allow_blank=True,
    )
    country          = serializers.CharField(max_length=2, required=False, allow_blank=True)
    password         = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('This username is already taken.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def validate_password(self, value):
        errors = [msg for check, msg in _PASSWORD_RULES if not check(value)]
        if errors:
            raise serializers.ValidationError(f"Password must have: {', '.join(errors)}.")
        return value

    def validate(self, data):
        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        from django.db import transaction

        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        gender   = validated_data.pop('gender', '')
        country  = validated_data.pop('country', '')
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data['username'],
                email=validated_data['email'],
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name'],
                password=password,
            )
            initials = (validated_data['first_name'][:1] + validated_data['last_name'][:1]).upper()
            UserProfile.objects.create(
                user=user,
                user_type=UserProfile.UserType.TEACHER,
                avatar_initials=initials,
                gender=gender,
                country=country,
            )
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    def get_avatar_url(self, obj):
        if not obj.avatar:
            return None
        request = self.context.get('request')
        url = obj.avatar.url
        return request.build_absolute_uri(url) if request else url

    class Meta:
        model  = UserProfile
        fields = ['user_type', 'avatar_initials', 'onboarding_completed',
                  'preferred_pillars', 'learning_style', 'gender', 'country', 'avatar_url']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'profile']


class AideaTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user, context=self.context).data
        return data
