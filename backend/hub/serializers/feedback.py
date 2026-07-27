from rest_framework import serializers

from hub.models import Feedback


class FeedbackSerializer(serializers.ModelSerializer):
    category_label   = serializers.CharField(source='get_category_display', read_only=True)
    status_label     = serializers.CharField(source='get_status_display', read_only=True)
    submitter_id     = serializers.IntegerField(source='user.id', read_only=True)
    submitter_name   = serializers.SerializerMethodField()

    class Meta:
        model  = Feedback
        fields = [
            'id', 'stream', 'category', 'category_label', 'message', 'attachments',
            'status', 'status_label', 'rejection_reason',
            'submitter_id', 'submitter_name', 'created_at',
        ]

    def get_submitter_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
