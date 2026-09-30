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

    def test_recompute_is_activity_weighted(self):
        """Progress % counts required *activities*, not resources: finishing one
        of two activities is 50% even though it holds more resources."""
        other = Activity.objects.create(module=self.module, title='B', order=2)
        r_other = Resource.objects.create(activity=other, type='text', order=1)
        ResourceProgress.objects.create(
            user=self.user, resource=r_other, completed_at='2026-01-01T00:00:00Z',
        )
        self.assertEqual(recompute_course_progress(self.user, self.enrollment), 50)

    def test_resource_path_mirrors_legacy_progress_once_activity_complete(self):
        from hub.models import LessonProgress
        record_resource_completion(self.user, self.enrollment, self.r_text)
        self.assertFalse(LessonProgress.objects.filter(user=self.user, lesson=self.activity).exists())
        record_resource_completion(self.user, self.enrollment, self.r_quiz, quiz_answers_raw=[0])
        lp = LessonProgress.objects.get(user=self.user, lesson=self.activity)
        self.assertEqual(lp.quiz_score, 1.0)


class LegacyCompletionDualWriteTest(TestCase):
    """The old activity-level endpoint completes every resource (building them
    on demand for resource-less activities) and still writes LessonProgress."""

    def setUp(self):
        self.user = User.objects.create_user(username='legacy', password='x')
        pillar = LearningPillar.objects.create(name='P', slug='p', order=1)
        course = Course.objects.create(title='C', pillar=pillar)
        module = Module.objects.create(title='M', course=course, order=1)
        self.activity = Activity.objects.create(
            module=module, title='Q', lesson_type='quiz', order=1, content='intro',
            quiz_data=[{'question': 'Q', 'options': [{'text': 'a', 'is_correct': True}]}],
        )
        self.enrollment = Enrollment.objects.create(user=self.user, course=course)

    def test_builds_resources_and_completes_them(self):
        from hub.completion import record_lesson_completion
        from hub.models import LessonProgress
        row, pct = record_lesson_completion(
            self.user, self.enrollment, self.activity, quiz_answers_raw=[0],
        )
        self.assertEqual(pct, 100)
        self.assertEqual(row.quiz_score, 1.0)
        self.assertEqual(self.activity.resources.count(), 2)  # text + quiz
        self.assertEqual(
            ResourceProgress.objects.filter(user=self.user, completed_at__isnull=False).count(), 2,
        )
        self.assertTrue(LessonProgress.objects.filter(user=self.user, lesson=self.activity).exists())
