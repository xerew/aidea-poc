from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import OnboardingQuestion, Subject, UserProfile
from hub.models.pathway import LearningPath, UserLearningPath


def _answers(pick):
    """Build a {question_id: option_id} map choosing, per active question, the
    option with the max score (pick='best') or min score (pick='worst')."""
    key = max if pick == 'best' else min
    out = {}
    for q in OnboardingQuestion.objects.filter(is_active=True).prefetch_related('options'):
        chosen = key(q.options.all(), key=lambda o: o.score)
        out[str(q.id)] = chosen.id
    return out


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
    'teaching_level': 'secondary',
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

    def test_returns_active_competency_questions(self):
        response = self.client.get(reverse('onboarding'))
        # 3 seeded questions, each with 4 options and no score leaked.
        self.assertEqual(len(response.data['questions']), 3)
        first = response.data['questions'][0]
        self.assertEqual(set(first.keys()), {'id', 'text', 'options'})
        self.assertEqual(set(first['options'][0].keys()), {'id', 'text'})

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
        self.subject = Subject.objects.get(slug='mathematics')
        self.payload = {**VALID_PAYLOAD, 'subject': self.subject.id, 'answers': _answers('best')}
        login = self.client.post(reverse('auth-login'), {'username': 'teacher1', 'password': 'pass'})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_correct_answers_score_6_and_assign_advanced_path(self, mock_task):
        response = self.client.post(reverse('onboarding'), self.payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['competency_score'], 6)
        self.assertEqual(response.data['competency_level'], 'advanced')
        self.assertEqual(response.data['pathway_name'], 'Advanced Integration')

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_profile_saved_correctly(self, mock_task):
        self.client.post(reverse('onboarding'), self.payload, format='json')
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.onboarding_completed)
        self.assertEqual(self.user.profile.subject_id, self.subject.id)
        self.assertEqual(self.user.profile.competency_score, 6)

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_user_learning_path_created(self, mock_task):
        self.client.post(reverse('onboarding'), self.payload, format='json')
        self.assertTrue(UserLearningPath.objects.filter(user=self.user).exists())

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_celery_task_fired(self, mock_task):
        self.client.post(reverse('onboarding'), self.payload, format='json')
        mock_task.assert_called_once_with(self.user.id)

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_wrong_answers_score_0_and_assign_beginner_path(self, mock_task):
        payload = {**self.payload, 'answers': _answers('worst')}
        response = self.client.post(reverse('onboarding'), payload, format='json')
        self.assertEqual(response.data['competency_score'], 0)
        self.assertEqual(response.data['competency_level'], 'beginner')
        self.assertEqual(response.data['pathway_name'], 'Beginner Foundations')

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_fallback_path_assigned_when_no_match(self, mock_task):
        LearningPath.objects.all().delete()
        LearningPath.objects.create(name='Beginner Foundations', slug='beginner-foundations', competency_min=0, competency_max=2)
        response = self.client.post(reverse('onboarding'), self.payload, format='json')
        self.assertEqual(response.data['pathway_name'], 'Beginner Foundations')

    def test_incomplete_answers_rejected(self):
        # Drop one answer — all active questions must be answered.
        partial = dict(list(self.payload['answers'].items())[:-1])
        payload = {**self.payload, 'answers': partial}
        response = self.client.post(reverse('onboarding'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_submit_twice_is_idempotent(self, mock_task):
        self.client.post(reverse('onboarding'), self.payload, format='json')
        response = self.client.post(reverse('onboarding'), self.payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(UserLearningPath.objects.filter(user=self.user).count(), 1)

    def test_invalid_subject_rejected(self):
        payload = {**self.payload, 'subject': 999999}
        response = self.client.post(reverse('onboarding'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_subject_rejected(self):
        payload = {**VALID_PAYLOAD}  # no 'subject'
        response = self.client.post(reverse('onboarding'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
