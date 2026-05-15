from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import Course, LearningPillar, UserProfile
from hub.models.recommendations import CourseRecommendation, RecommendationEvent


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


class RecommendationSourceFieldTest(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        login = self.client.post(reverse('auth-login'), {'username': 'teacher1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')

    def test_source_personal_in_response(self):
        pillar = LearningPillar.objects.create(name='SP', slug='sp', description='')
        course = Course.objects.create(
            title='Source Test', pillar=pillar, level='beginner', is_published=True,
        )
        CourseRecommendation.objects.create(
            user=self.user, course=course, score=0.9, reason='test', source='personal',
        )
        response = self.client.get(reverse('recommendations'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['source'], 'personal')

    def test_source_cf_in_response(self):
        pillar = LearningPillar.objects.create(name='CF', slug='cf', description='')
        course = Course.objects.create(
            title='CF Test', pillar=pillar, level='beginner', is_published=True,
        )
        CourseRecommendation.objects.create(
            user=self.user, course=course, score=0.6, reason='67% of STEM', source='cf',
        )
        response = self.client.get(reverse('recommendations'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['source'], 'cf')


class RecommendationEventAPITest(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        login = self.client.post(reverse('auth-login'), {'username': 'teacher1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        pillar = LearningPillar.objects.create(name='EV', slug='ev', description='')
        self.course = Course.objects.create(
            title='Event Course', pillar=pillar, level='beginner', is_published=True,
        )

    def test_shown_event_created(self):
        response = self.client.post(reverse('recommendation-event'), {
            'course_id': self.course.id,
            'event_type': 'shown',
            'rank': 1,
            'source': 'personal',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(RecommendationEvent.objects.count(), 1)
        ev = RecommendationEvent.objects.first()
        self.assertEqual(ev.event_type, 'shown')
        self.assertEqual(ev.source, 'personal')
        self.assertIn('alpha', ev.weights_snapshot)

    def test_clicked_event_created(self):
        response = self.client.post(reverse('recommendation-event'), {
            'course_id': self.course.id,
            'event_type': 'clicked',
            'rank': 2,
            'source': 'cf',
        })
        self.assertEqual(response.status_code, 201)
        ev = RecommendationEvent.objects.first()
        self.assertEqual(ev.rank, 2)

    def test_invalid_event_type_rejected(self):
        response = self.client.post(reverse('recommendation-event'), {
            'course_id': self.course.id,
            'event_type': 'unknown_type',
            'rank': 1,
            'source': 'personal',
        })
        self.assertEqual(response.status_code, 400)

    def test_invalid_source_rejected(self):
        response = self.client.post(reverse('recommendation-event'), {
            'course_id': self.course.id,
            'event_type': 'shown',
            'rank': 1,
            'source': 'invalid',
        })
        self.assertEqual(response.status_code, 400)

    def test_content_creator_gets_403(self):
        from hub.models import UserProfile as UP
        creator = User.objects.create_user(username='creator2', password='pass')
        UP.objects.create(user=creator, user_type=UP.UserType.CONTENT_CREATOR)
        login = self.client.post(reverse('auth-login'), {'username': 'creator2', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        response = self.client.post(reverse('recommendation-event'), {
            'course_id': self.course.id, 'event_type': 'shown', 'rank': 1, 'source': 'personal',
        })
        self.assertEqual(response.status_code, 403)
