from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from hub.models import Course, Enrollment, LearningPillar
from hub.models.content import Lesson, Module
from hub.models.user import UserProfile


class EnrollmentCompletedAtTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ca1', password='pass')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        pillar = LearningPillar.objects.create(name='PA', slug='pa', description='')
        self.course = Course.objects.create(title='TA', pillar=pillar)
        module = Module.objects.create(title='MA', course=self.course, order=1)
        self.lesson = Lesson.objects.create(
            title='LA', module=module, order=1, is_required=True
        )
        self.enrollment = Enrollment.objects.create(user=self.user, course=self.course)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_completed_at_is_null_initially(self):
        self.assertIsNone(self.enrollment.completed_at)

    def test_completed_at_set_when_progress_reaches_100(self):
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{self.lesson.pk}/complete/'
        )
        self.enrollment.refresh_from_db()
        self.assertIsNotNone(self.enrollment.completed_at)

    def test_completed_at_not_overwritten_on_repeat_call(self):
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{self.lesson.pk}/complete/'
        )
        self.enrollment.refresh_from_db()
        first_ts = self.enrollment.completed_at
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{self.lesson.pk}/complete/'
        )
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.completed_at, first_ts)

    def test_completed_at_not_set_on_partial_completion(self):
        module = self.course.modules.first()
        Lesson.objects.create(title='LA2', module=module, order=2, is_required=True)
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{self.lesson.pk}/complete/'
        )
        self.enrollment.refresh_from_db()
        self.assertIsNone(self.enrollment.completed_at)

    def test_completed_at_exposed_in_my_learning_api(self):
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{self.lesson.pk}/complete/'
        )
        response = self.client.get('/api/my-learning/')
        self.assertEqual(response.status_code, 200)
        completed = response.data['completed']
        self.assertEqual(len(completed), 1)
        self.assertIn('completed_at', completed[0])
        self.assertIsNotNone(completed[0]['completed_at'])


class CompetencyProgressionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cp1', password='pass')
        self.profile = UserProfile.objects.create(
            user=self.user,
            user_type=UserProfile.UserType.TEACHER,
            competency_score=0,
            onboarding_completed=True,
        )
        pillar = LearningPillar.objects.create(name='PB', slug='pb', description='')
        self.course = Course.objects.create(title='TB', pillar=pillar)
        module = Module.objects.create(title='MB', course=self.course, order=1)
        self.lesson = Lesson.objects.create(
            title='LB', module=module, order=1, is_required=True
        )
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_score_increments_on_course_completion(self):
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{self.lesson.pk}/complete/'
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.competency_score, 1)

    def test_score_not_incremented_on_partial_completion(self):
        module = self.course.modules.first()
        Lesson.objects.create(title='LB2', module=module, order=2, is_required=True)
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{self.lesson.pk}/complete/'
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.competency_score, 0)

    def test_score_capped_at_6(self):
        self.profile.competency_score = 6
        self.profile.save()
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{self.lesson.pk}/complete/'
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.competency_score, 6)

    def test_score_increments_only_once_per_completion(self):
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{self.lesson.pk}/complete/'
        )
        self.client.post(
            f'/api/courses/{self.course.pk}/lessons/{self.lesson.pk}/complete/'
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.competency_score, 1)
