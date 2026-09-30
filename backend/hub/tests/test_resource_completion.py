from django.contrib.auth.models import User
from django.test import TestCase

from hub.completion import recompute_course_progress, record_resource_completion
from hub.models import (
    Activity,
    Course,
    Enrollment,
    LearningPillar,
    Module,
    Resource,
    ResourceProgress,
)


class ResourceCompletionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='learner', password='x')
        pillar = LearningPillar.objects.create(name='P', slug='p', order=1)
        self.course = Course.objects.create(title='C', pillar=pillar)
        self.module = Module.objects.create(title='M', course=self.course, order=1)
        self.activity = Activity.objects.create(module=self.module, title='A', order=1)
        self.r_text = Resource.objects.create(activity=self.activity, type='text', order=1)
        self.r_quiz = Resource.objects.create(
            activity=self.activity, type='quiz', order=2,
            quiz_data=[{'question': 'Q', 'options': [{'text': 'a', 'is_correct': True},
                                                     {'text': 'b', 'is_correct': False}]}],
        )
        self.r_opt = Resource.objects.create(
            activity=self.activity, type='text', order=3, is_required=False,
        )
        self.enrollment = Enrollment.objects.create(user=self.user, course=self.course)

    def test_activity_completes_only_when_required_resources_done(self):
        record_resource_completion(self.user, self.enrollment, self.r_text)
        self.enrollment.refresh_from_db()
        self.assertLess(self.enrollment.progress_pct, 100)   # quiz still pending

        record_resource_completion(self.user, self.enrollment, self.r_quiz, quiz_answers_raw=[0])
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.progress_pct, 100)  # optional resource doesn't block

    def test_quiz_score_recorded_on_resource(self):
        rp, _ = record_resource_completion(self.user, self.enrollment, self.r_quiz, quiz_answers_raw=[0])
        self.assertEqual(rp.quiz_score, 1.0)
        rp2 = ResourceProgress.objects.get(user=self.user, resource=self.r_quiz)
        self.assertEqual(rp2.quiz_score, 1.0)

    def test_idempotent(self):
        record_resource_completion(self.user, self.enrollment, self.r_text)
        record_resource_completion(self.user, self.enrollment, self.r_text)
        self.assertEqual(
            ResourceProgress.objects.filter(user=self.user, resource=self.r_text).count(), 1,
        )

    def test_recompute_only(self):
        ResourceProgress.objects.create(
            user=self.user, resource=self.r_text, completed_at='2026-01-01T00:00:00Z',
        )
        pct = recompute_course_progress(self.user, self.enrollment)
        self.assertGreater(pct, 0)
        self.assertLess(pct, 100)
