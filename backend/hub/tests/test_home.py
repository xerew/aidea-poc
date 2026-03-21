from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import Course, Enrollment, LearningPillar, Module, UserProfile


class HomeViewTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='teacher1',
            password='testpass123',
            first_name='Nikos',
            last_name='Grammatikos',
        )
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)

        self.pillar1 = LearningPillar.objects.create(
            name='Teach with AI', slug='teach-with-ai',
            description='Learn to use AI tools.', order=1,
        )
        self.pillar2 = LearningPillar.objects.create(
            name='Teach for AI', slug='teach-for-ai',
            description='Prepare students for AI.', order=2,
        )

        self.course1 = Course.objects.create(title='Course 1', pillar=self.pillar1)
        self.course2 = Course.objects.create(title='Course 2', pillar=self.pillar1)
        self.module1 = Module.objects.create(title='Module 1', course=self.course1, order=1)
        self.module2 = Module.objects.create(title='Module 2', course=self.course1, order=2)

        self.client.force_authenticate(user=self.user)

    def test_home_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_home_no_enrollments(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['continue_learning'])
        self.assertEqual(len(response.data['pillars']), 2)

    def test_home_continue_learning(self):
        Enrollment.objects.create(
            user=self.user,
            course=self.course1,
            current_module=self.module2,
            progress_pct=65,
        )
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cl = response.data['continue_learning']
        self.assertEqual(cl['course_title'], 'Course 1')
        self.assertEqual(cl['current_module_title'], 'Module 2')
        self.assertEqual(cl['progress_pct'], 65)

    def test_home_pillars_course_count(self):
        response = self.client.get(reverse('home'))
        pillars = {p['slug']: p for p in response.data['pillars']}
        self.assertEqual(pillars['teach-with-ai']['course_count'], 2)
        self.assertEqual(pillars['teach-for-ai']['course_count'], 0)

    def test_home_pillars_progress_no_enrollments(self):
        response = self.client.get(reverse('home'))
        for pillar in response.data['pillars']:
            self.assertEqual(pillar['progress_pct'], 0)

    def test_home_pillars_progress_with_enrollments(self):
        Enrollment.objects.create(user=self.user, course=self.course1, progress_pct=40)
        Enrollment.objects.create(user=self.user, course=self.course2, progress_pct=60)
        response = self.client.get(reverse('home'))
        pillars = {p['slug']: p for p in response.data['pillars']}
        self.assertEqual(pillars['teach-with-ai']['progress_pct'], 50)
        self.assertEqual(pillars['teach-for-ai']['progress_pct'], 0)

    def test_home_continue_learning_is_most_recently_accessed(self):
        Enrollment.objects.create(
            user=self.user, course=self.course1, progress_pct=30,
        )
        enrollment2 = Enrollment.objects.create(
            user=self.user, course=self.course2, progress_pct=80,
        )
        # Touch enrollment2 so it becomes most recently accessed
        enrollment2.save()
        response = self.client.get(reverse('home'))
        self.assertEqual(response.data['continue_learning']['course_title'], 'Course 2')
