from rest_framework import serializers

from hub.models import AssignmentSubmission


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AssignmentSubmission
        fields = ['id', 'status', 'text', 'feedback', 'submitted_at', 'reviewed_at']


class ReviewQueueSerializer(serializers.ModelSerializer):
    learner_name = serializers.SerializerMethodField()
    course_title = serializers.CharField(source='lesson.module.course.title', read_only=True)
    course_id    = serializers.IntegerField(source='lesson.module.course.id', read_only=True)
    module_title = serializers.CharField(source='lesson.module.title', read_only=True)
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)

    class Meta:
        model  = AssignmentSubmission
        fields = ['id', 'learner_name', 'course_id', 'course_title', 'module_title',
                  'lesson_title', 'text', 'feedback', 'submitted_at']

    def get_learner_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
