from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from hub.models import (
    Activity,
    Course,
    Enrollment,
    LearningPillar,
    Module,
    Resource,
    ResourceProgress,
    UserProfile,
)


class ResourceLearnerTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='learner', password='x')
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)
        pillar = LearningPillar.objects.create(name='P', slug='p', order=1)
        self.course = Course.objects.create(title='C', pillar=pillar, is_published=True)
        module = Module.objects.create(title='M', course=self.course, order=1)
        self.activity = Activity.objects.create(module=module, title='A', order=1)
        self.r_text = Resource.objects.create(activity=self.activity, type='text', order=1)
        self.r_quiz = Resource.objects.create(
            activity=self.activity, type='quiz', order=2,
            quiz_data=[{'question': 'Q', 'options': [
                {'text': 'a', 'is_correct': True}, {'text': 'b', 'is_correct': False}]}],
        )
        self.enrollment = Enrollment.objects.create(user=self.user, course=self.course)
        self.client.force_authenticate(self.user)

    def _url(self, name, resource):
        return reverse(name, kwargs={
            'pk': self.course.pk, 'lesson_pk': self.activity.pk, 'resource_pk': resource.pk})

    def test_complete_text_resource(self):
        res = self.client.post(self._url('resource-complete', self.r_text), {}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data['is_completed'])
        self.assertTrue(ResourceProgress.objects.filter(
            user=self.user, resource=self.r_text, completed_at__isnull=False).exists())

    def test_quiz_check(self):
        res = self.client.post(self._url('resource-quiz-check', self.r_quiz),
                               {'question_index': 0, 'selected': 0}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data['correct'])
        self.assertEqual(res.data['correct_index'], 0)

    def test_complete_quiz_resource_records_score(self):
        res = self.client.post(self._url('resource-complete', self.r_quiz),
                               {'quiz_answers': [0]}, format='json')
        self.assertEqual(res.status_code, 200)
        rp = ResourceProgress.objects.get(user=self.user, resource=self.r_quiz)
        self.assertEqual(rp.quiz_score, 1.0)

    def test_not_enrolled_blocked(self):
        other = User.objects.create_user(username='intruder', password='x')
        UserProfile.objects.create(user=other, user_type=UserProfile.UserType.TEACHER)
        self.client.force_authenticate(other)
        res = self.client.post(self._url('resource-complete', self.r_text), {}, format='json')
        self.assertEqual(res.status_code, 403)
