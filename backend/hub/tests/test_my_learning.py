from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import Course, Enrollment, LearningPillar, Module, UserProfile


class MyLearningViewTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='teacher1',
            password='testpass123',
            first_name='Nikos',
            last_name='Grammatikos',
        )
        UserProfile.objects.create(user=self.user, user_type=UserProfile.UserType.TEACHER)

        self.pillar = LearningPillar.objects.create(
            name='Teach with AI', slug='teach-with-ai',
            description='Learn to use AI tools.', order=1,
        )
        self.pillar2 = LearningPillar.objects.create(
            name='Teach about AI', slug='teach-about-ai',
            description='Teach students about AI.', order=2,
        )

        self.course1 = Course.objects.create(
            title='Introduction to AI Tools for Teachers', pillar=self.pillar,
        )
        self.course2 = Course.objects.create(
            title='AI-Generated Content in Teaching', pillar=self.pillar2,
        )
        self.course3 = Course.objects.create(
            title='Creative Teaching with AI', pillar=self.pillar2,
        )

        self.module1 = Module.objects.create(title='Module 1', course=self.course1, order=1)
        self.module2 = Module.objects.create(title='Prompt Engineering', course=self.course1, order=2)

        self.client.force_authenticate(user=self.user)
        self.url = reverse('my-learning')

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_enrollments(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['continue_learning'])
        self.assertEqual(response.data['in_progress'], [])
        self.assertEqual(response.data['completed'], [])

    def test_in_progress_enrollment(self):
        Enrollment.objects.create(
            user=self.user,
            course=self.course1,
            current_module=self.module2,
            progress_pct=65,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['in_progress']), 1)
        self.assertEqual(response.data['completed'], [])

        item = response.data['in_progress'][0]
        self.assertEqual(item['course_id'], self.course1.id)
        self.assertEqual(item['course_title'], 'Introduction to AI Tools for Teachers')
        self.assertEqual(item['pillar_name'], 'Teach with AI')
        self.assertEqual(item['pillar_slug'], 'teach-with-ai')
        self.assertEqual(item['progress_pct'], 65)
        self.assertEqual(item['current_module_title'], 'Prompt Engineering')
        self.assertIsNotNone(item['last_accessed_at'])
        self.assertIsNotNone(item['enrolled_at'])

    def test_module_count_field(self):
        Enrollment.objects.create(user=self.user, course=self.course1, progress_pct=50)
        response = self.client.get(self.url)
        self.assertEqual(response.data['in_progress'][0]['module_count'], 2)

    def test_completed_enrollment(self):
        Enrollment.objects.create(
            user=self.user,
            course=self.course3,
            progress_pct=100,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['in_progress'], [])
        self.assertEqual(len(response.data['completed']), 1)

        item = response.data['completed'][0]
        self.assertEqual(item['course_id'], self.course3.id)
        self.assertEqual(item['course_title'], 'Creative Teaching with AI')
        self.assertEqual(item['progress_pct'], 100)

    def test_continue_learning_is_most_recent_in_progress(self):
        enrollment1 = Enrollment.objects.create(
            user=self.user, course=self.course1, progress_pct=30,
        )
        enrollment2 = Enrollment.objects.create(
            user=self.user, course=self.course2, progress_pct=50,
        )
        # Touch enrollment2 to make it more recently accessed
        enrollment2.save()
        # Verify enrollment2 is more recent
        enrollment1.refresh_from_db()
        enrollment2.refresh_from_db()
        self.assertGreater(enrollment2.last_accessed_at, enrollment1.last_accessed_at)

        response = self.client.get(self.url)
        cl = response.data['continue_learning']
        self.assertIsNotNone(cl)
        self.assertEqual(cl['course_id'], self.course2.id)

    def test_continue_learning_none_when_all_completed(self):
        Enrollment.objects.create(user=self.user, course=self.course1, progress_pct=100)
        Enrollment.objects.create(user=self.user, course=self.course2, progress_pct=100)
        response = self.client.get(self.url)
        self.assertIsNone(response.data['continue_learning'])
        self.assertEqual(len(response.data['completed']), 2)

    def test_mixed_enrollments(self):
        Enrollment.objects.create(user=self.user, course=self.course1, progress_pct=65)
        Enrollment.objects.create(user=self.user, course=self.course2, progress_pct=30)
        Enrollment.objects.create(user=self.user, course=self.course3, progress_pct=100)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['continue_learning'])
        self.assertEqual(len(response.data['in_progress']), 2)
        self.assertEqual(len(response.data['completed']), 1)

    def test_no_cross_user_data_leakage(self):
        other_user = User.objects.create_user(username='other', password='pass')
        UserProfile.objects.create(user=other_user, user_type=UserProfile.UserType.TEACHER)
        Enrollment.objects.create(user=other_user, course=self.course1, progress_pct=80)

        response = self.client.get(self.url)
        self.assertEqual(response.data['in_progress'], [])
        self.assertEqual(response.data['completed'], [])
        self.assertIsNone(response.data['continue_learning'])

    def test_current_module_title_null_when_not_set(self):
        Enrollment.objects.create(
            user=self.user,
            course=self.course1,
            current_module=None,
            progress_pct=10,
        )
        response = self.client.get(self.url)
        item = response.data['in_progress'][0]
        self.assertIsNone(item['current_module_title'])
