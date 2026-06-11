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
