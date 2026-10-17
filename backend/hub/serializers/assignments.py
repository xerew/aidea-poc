from rest_framework import serializers

from hub.models import AIReview, AssignmentSubmission


def latest_ai_review(submission):
    return submission.ai_reviews.exclude(status=AIReview.Status.FAILED).first()


def _criterion_names(review, language=None, translations=None):
    names = {c['id']: c['name'] for c in review.rubric or []}
    if language and translations:
        names.update((translations or {}).get(language, {}))
    return names


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    ai_precheck = serializers.SerializerMethodField()

    class Meta:
        model  = AssignmentSubmission
        fields = ['id', 'status', 'text', 'attachments', 'feedback', 'submitted_at', 'reviewed_at', 'ai_precheck']

    def get_ai_precheck(self, obj):
        config = getattr(obj.resource, 'ai_review_config', None) if obj.resource_id else None
        if config is None or not config.learner_visible:
            return None
        review = latest_ai_review(obj)
        if review is None:
            return None
        if review.status != AIReview.Status.DONE:
            return {'status': review.status, 'criteria': [], 'feedback': ''}
        request = self.context.get('request')
        language = getattr(getattr(getattr(request, 'user', None), 'profile', None), 'language', None)
        names = _criterion_names(review, language, config.criteria_translations)
        return {
            'status': 'done',
            'criteria': [{'name': names.get(c['id'], c['id']), 'status': c['status'], 'reason': c['reason']}
                         for c in review.criteria_results],
            'feedback': review.learner_feedback,
        }


class ReviewQueueSerializer(serializers.ModelSerializer):
    learner_name = serializers.SerializerMethodField()
    learner_id   = serializers.IntegerField(source='user.id', read_only=True)
    course_title = serializers.CharField(source='lesson.module.course.title', read_only=True)
    course_id    = serializers.IntegerField(source='lesson.module.course.id', read_only=True)
    module_title = serializers.CharField(source='lesson.module.title', read_only=True)
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)
    ai_review    = serializers.SerializerMethodField()

    class Meta:
        model  = AssignmentSubmission
        fields = ['id', 'status', 'learner_name', 'learner_id', 'course_id', 'course_title', 'module_title',
                  'lesson_title', 'text', 'attachments', 'feedback', 'submitted_at', 'ai_review']

    def get_learner_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_ai_review(self, obj):
        review = latest_ai_review(obj)
        if review is None:
            return None
        names = _criterion_names(review)
        return {
            'status': review.status, 'verdict': review.verdict, 'confidence': review.confidence,
            'criteria': [{'id': c['id'], 'name': names.get(c['id'], c['id']), 'status': c['status'], 'reason': c['reason']}
                         for c in review.criteria_results],
            'learner_feedback': review.learner_feedback, 'reviewer_notes': review.reviewer_notes,
            'duplicates': (review.checks or {}).get('duplicates', []),
            'auto_approved': review.auto_approved, 'spot_check': review.spot_check,
        }
