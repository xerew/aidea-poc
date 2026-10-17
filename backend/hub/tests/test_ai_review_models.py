from django.contrib.auth.models import User
from django.test import TestCase

from hub.models import (
    Activity,
    AIReview,
    AIReviewSettings,
    AssignmentReviewConfig,
    AssignmentSubmission,
    Course,
    LearningPillar,
    Module,
    Resource,
    UserProfile,
)


def make_assignment(title='AI course'):
    pillar = LearningPillar.objects.get_or_create(slug='p-air', defaults={'name': 'P', 'order': 1})[0]
    course = Course.objects.create(title=title, pillar=pillar, level='beginner', duration_hours=1, is_published=True)
    module = Module.objects.create(course=course, title='M', order=1)
    activity = Activity.objects.create(module=module, title='Task', order=1)
    resource = Resource.objects.create(activity=activity, type='assignment', order=1,
                                       instructions='<p>Describe three AI risks.</p>')
    return course, module, activity, resource


class AIReviewModelTests(TestCase):
    def test_settings_singleton_defaults(self):
        s = AIReviewSettings.get()
        self.assertEqual((s.enabled, s.model_name, s.confidence_threshold, s.spot_check_rate,
                          s.unlock_min_reviews, s.unlock_min_lower_bound),
                         (False, 'qwen2.5vl:32b', 0.8, 0.1, 30, 0.9))
        self.assertEqual(AIReviewSettings.get().pk, s.pk)

    def test_config_ready_only_when_enabled_approved_with_criteria(self):
        *_, resource = make_assignment()
        config = AssignmentReviewConfig.objects.create(resource=resource)
        self.assertFalse(config.is_ready())
        config.enabled = True
        config.criteria = [{'id': 'c1', 'name': 'Risks', 'met': 'Names 3 risks', 'required': True}]
        self.assertFalse(config.is_ready())
        config.rubric_approved = True
        self.assertTrue(config.is_ready())
        self.assertTrue(config.duplicate_check)
        self.assertFalse(config.learner_visible or config.auto_approve)

    def test_ai_review_flagged_and_resource(self):
        *_, activity, resource = make_assignment()
        user = User.objects.create_user('air_l', password='x')
        UserProfile.objects.create(user=user)
        sub = AssignmentSubmission.objects.create(user=user, lesson=activity, resource=resource, text='t')
        review = AIReview.objects.create(submission=sub, rubric=[])
        self.assertEqual((review.status, review.flagged, review.resource), ('queued', False, resource))
        self.assertEqual((review.feedback_used, review.feedback_similarity), (False, None))
        review.checks = {'duplicates': [{'submission_id': 9}]}
        self.assertTrue(review.flagged)

    def test_opt_out_default(self):
        user = User.objects.create_user('air_o', password='x')
        self.assertFalse(UserProfile.objects.create(user=user).ai_training_opt_out)
