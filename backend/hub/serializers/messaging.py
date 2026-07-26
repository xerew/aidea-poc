from rest_framework import serializers

from hub.models import Message


def user_brief(user, request=None):
    """Compact identity block for the person on the other side of a thread."""
    profile = getattr(user, 'profile', None)
    avatar_url = None
    if profile and profile.avatar:
        url = profile.avatar.url
        avatar_url = request.build_absolute_uri(url) if request else url
    return {
        'id': user.id,
        'name': user.get_full_name() or user.username,
        'user_type': getattr(profile, 'user_type', ''),
        'avatar_url': avatar_url,
        'avatar_initials': getattr(profile, 'avatar_initials', ''),
        'gender': getattr(profile, 'gender', ''),
    }


class MessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)
    is_mine   = serializers.SerializerMethodField()

    class Meta:
        model  = Message
        fields = ['id', 'sender_id', 'is_mine', 'text', 'created_at', 'read_at']

    def get_is_mine(self, obj):
        request = self.context.get('request')
        return bool(request and obj.sender_id == request.user.id)


class ConversationListSerializer(serializers.Serializer):
    """One row in the conversation list: the other person plus a preview."""
    id            = serializers.IntegerField()
    other_user    = serializers.SerializerMethodField()
    last_message  = serializers.SerializerMethodField()
    last_at       = serializers.SerializerMethodField()
    unread_count  = serializers.SerializerMethodField()

    def _messages(self, obj):
        # Uses the prefetched cache (Message default ordering is by created_at).
        return list(obj.messages.all())

    def get_other_user(self, obj):
        request = self.context.get('request')
        return user_brief(obj.other_user(request.user), request)

    def get_last_message(self, obj):
        messages = self._messages(obj)
        return messages[-1].text if messages else ''

    def get_last_at(self, obj):
        messages = self._messages(obj)
        return messages[-1].created_at if messages else obj.updated_at

    def get_unread_count(self, obj):
        me = self.context['request'].user.id
        return sum(1 for m in self._messages(obj) if m.sender_id != me and m.read_at is None)
