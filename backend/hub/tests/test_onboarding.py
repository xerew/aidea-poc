from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import UserProfile
from hub.models.pathway import LearningPath, UserLearningPath


def make_teacher(username='teacher1', onboarding=False):
    user = User.objects.create_user(username=username, password='pass')
    UserProfile.objects.create(
        user=user,
        user_type=UserProfile.UserType.TEACHER,
        onboarding_completed=onboarding,
    )
    return user


def make_path(slug, competency_min, competency_max):
    return LearningPath.objects.create(
        name=slug.replace('-', ' ').title(),
        slug=slug,
        competency_min=competency_min,
        competency_max=competency_max,
    )


VALID_PAYLOAD = {
    'subject_area':   'stem',
    'teaching_level': 'secondary',
    'answers':        {'q3': 'b', 'q4': 'b', 'q5': 'b'},
    'goals':          ['save_time'],
}


class OnboardingGetTestCase(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        login = self.client.post(reverse('auth-login'), {'username': 'teacher1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')

    def test_returns_not_completed_for_new_teacher(self):
        response = self.client.get(reverse('onboarding'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['completed'])
        self.assertIsNone(response.data['competency_level'])

    def test_content_creator_cannot_access(self):
        creator = User.objects.create_user(username='creator1', password='pass')
        UserProfile.objects.create(user=creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        login = self.client.post(reverse('auth-login'), {'username': 'creator1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        response = self.client.get(reverse('onboarding'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class OnboardingPostTestCase(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        make_path('beginner-foundations', 0, 2)
        make_path('intermediate-growth', 3, 4)
        make_path('advanced-integration', 5, 6)
        login = self.client.post(reverse('auth-login'), {'username': 'teacher1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_correct_answers_score_6_and_assign_advanced_path(self, mock_task):
        response = self.client.post(reverse('onboarding'), VALID_PAYLOAD, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['competency_score'], 6)
        self.assertEqual(response.data['competency_level'], 'advanced')
        self.assertEqual(response.data['pathway_name'], 'Advanced Integration')

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_profile_saved_correctly(self, mock_task):
        self.client.post(reverse('onboarding'), VALID_PAYLOAD, format='json')
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.onboarding_completed)
        self.assertEqual(self.user.profile.subject_area, 'stem')
        self.assertEqual(self.user.profile.competency_score, 6)

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_user_learning_path_created(self, mock_task):
        self.client.post(reverse('onboarding'), VALID_PAYLOAD, format='json')
        self.assertTrue(UserLearningPath.objects.filter(user=self.user).exists())

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_celery_task_fired(self, mock_task):
        self.client.post(reverse('onboarding'), VALID_PAYLOAD, format='json')
        mock_task.assert_called_once_with(self.user.id)

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_wrong_answers_score_0_and_assign_beginner_path(self, mock_task):
        payload = {**VALID_PAYLOAD, 'answers': {'q3': 'a', 'q4': 'a', 'q5': 'a'}}
        response = self.client.post(reverse('onboarding'), payload, format='json')
        self.assertEqual(response.data['competency_score'], 0)
        self.assertEqual(response.data['competency_level'], 'beginner')
        self.assertEqual(response.data['pathway_name'], 'Beginner Foundations')

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_fallback_path_assigned_when_no_match(self, mock_task):
        LearningPath.objects.all().delete()
        LearningPath.objects.create(name='Beginner Foundations', slug='beginner-foundations', competency_min=0, competency_max=2)
        payload = {**VALID_PAYLOAD, 'answers': {'q3': 'b', 'q4': 'b', 'q5': 'b'}}
        response = self.client.post(reverse('onboarding'), payload, format='json')
        self.assertEqual(response.data['pathway_name'], 'Beginner Foundations')

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_submit_twice_is_idempotent(self, mock_task):
        self.client.post(reverse('onboarding'), VALID_PAYLOAD, format='json')
        response = self.client.post(reverse('onboarding'), VALID_PAYLOAD, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(UserLearningPath.objects.filter(user=self.user).count(), 1)

    def test_invalid_subject_area_rejected(self):
        payload = {**VALID_PAYLOAD, 'subject_area': 'invalid'}
        response = self.client.post(reverse('onboarding'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
