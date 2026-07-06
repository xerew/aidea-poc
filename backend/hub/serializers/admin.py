from django.contrib.auth.models import User
from rest_framework import serializers

from hub.models import AccessRequest, UserProfile


class AdminUserSerializer(serializers.ModelSerializer):
    user_type       = serializers.CharField(source='profile.user_type')
    avatar_initials = serializers.CharField(source='profile.avatar_initials')

    class Meta:
        model  = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email',
                  'user_type', 'avatar_initials']


class AdminUserRoleSerializer(serializers.Serializer):
    user_type = serializers.ChoiceField(choices=UserProfile.UserType.choices)


class AccessRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AccessRequest
        fields = ['id', 'status', 'message', 'denial_reason', 'denial_seen', 'created_at']
        read_only_fields = ['id', 'status', 'denial_reason', 'denial_seen', 'created_at']


class AccessRequestAdminSerializer(serializers.ModelSerializer):
    username        = serializers.CharField(source='user.username',                read_only=True)
    first_name      = serializers.CharField(source='user.first_name',              read_only=True)
    last_name       = serializers.CharField(source='user.last_name',               read_only=True)
    avatar_initials = serializers.CharField(source='user.profile.avatar_initials', read_only=True)

    class Meta:
        model  = AccessRequest
        fields = ['id', 'username', 'first_name', 'last_name', 'avatar_initials',
                  'message', 'status', 'denial_reason', 'created_at', 'reviewed_at']
