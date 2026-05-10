from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import Course, LearningPillar, UserProfile
from hub.models.recommendations import CourseRecommendation


def make_teacher(username='teacher1'):
    user = User.objects.create_user(username=username, password='pass')
    UserProfile.objects.create(user=user, user_type=UserProfile.UserType.TEACHER)
    return user


class RecommendationsGetTestCase(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        login = self.client.post(reverse('auth-login'), {'username': 'teacher1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')

    def test_empty_list_when_no_recommendations(self):
        response = self.client.get(reverse('recommendations'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_returns_precomputed_recommendations(self):
        pillar = LearningPillar.objects.create(name='P', slug='p', description='')
        course = Course.objects.create(title='AI Basics', pillar=pillar, level='beginner', is_published=True)
        CourseRecommendation.objects.create(
            user=self.user, course=course, score=0.95,
            reason='Matches your beginner level and stem focus',
        )
        response = self.client.get(reverse('recommendations'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'AI Basics')
        self.assertEqual(response.data[0]['score'], 0.95)

    def test_content_creator_gets_403(self):
        creator = User.objects.create_user(username='creator1', password='pass')
        UserProfile.objects.create(user=creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        login = self.client.post(reverse('auth-login'), {'username': 'creator1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        response = self.client.get(reverse('recommendations'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
