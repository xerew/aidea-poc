from django.contrib.auth.models import User
from django.test import TestCase

from hub.models import Course, LearningPillar, Lesson, LessonProgress, Module


class LessonProgressFieldsTest(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='lp1', password='pass')
        pillar = LearningPillar.objects.create(name='P1', slug='p1', description='')
        course = Course.objects.create(title='C1', pillar=pillar)
        module = Module.objects.create(title='M1', course=course, order=1)
        lesson = Lesson.objects.create(title='L1', module=module, order=1, is_required=True)
        self.lp = LessonProgress.objects.create(user=user, lesson=lesson)

    def test_time_spent_seconds_null_by_default(self):
        self.assertIsNone(self.lp.time_spent_seconds)

    def test_quiz_score_null_by_default(self):
        self.assertIsNone(self.lp.quiz_score)

    def test_quiz_answers_empty_by_default(self):
        self.assertEqual(self.lp.quiz_answers, [])

    def test_engagement_data_empty_by_default(self):
        self.assertEqual(self.lp.engagement_data, {})

    def test_completed_at_null_by_default(self):
        self.assertIsNone(self.lp.completed_at)


class LessonSessionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ls1', password='pass')
        pillar = LearningPillar.objects.create(name='P2', slug='p2', description='')
        course = Course.objects.create(title='C2', pillar=pillar)
        module = Module.objects.create(title='M2', course=course, order=1)
        self.lesson = Lesson.objects.create(title='L2', module=module, order=1, is_required=True)

    def test_session_created_with_started_at(self):
        from hub.models.activity import LessonSession
        session = LessonSession.objects.create(user=self.user, lesson=self.lesson)
        self.assertIsNotNone(session.started_at)

    def test_multiple_sessions_allowed_for_same_user_lesson(self):
        from hub.models.activity import LessonSession
        LessonSession.objects.create(user=self.user, lesson=self.lesson)
        LessonSession.objects.create(user=self.user, lesson=self.lesson)
        self.assertEqual(
            LessonSession.objects.filter(user=self.user, lesson=self.lesson).count(), 2
        )


class LearnerActivityConfigTest(TestCase):
    def test_get_creates_singleton(self):
        from hub.models.activity import LearnerActivityConfig
        config = LearnerActivityConfig.get()
        self.assertEqual(config.pk, 1)

    def test_get_returns_same_instance(self):
        from hub.models.activity import LearnerActivityConfig
        config1 = LearnerActivityConfig.get()
        config2 = LearnerActivityConfig.get()
        self.assertEqual(LearnerActivityConfig.objects.count(), 1)
        self.assertEqual(config1.pk, config2.pk)

    def test_defaults(self):
        from hub.models.activity import LearnerActivityConfig
        config = LearnerActivityConfig.get()
        self.assertFalse(config.quiz_affects_competency)
        self.assertAlmostEqual(config.quiz_pass_threshold, 0.7)
        self.assertAlmostEqual(config.quiz_weight_pass, 1.0)
        self.assertAlmostEqual(config.quiz_weight_fail, 0.5)

    def test_save_enforces_singleton(self):
        from hub.models.activity import LearnerActivityConfig
        config = LearnerActivityConfig.get()
        config.quiz_affects_competency = True
        config.save()
        self.assertEqual(LearnerActivityConfig.objects.count(), 1)
        self.assertEqual(config.pk, 1)
