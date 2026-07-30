from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import OnboardingDimension, OnboardingQuestion, UserProfile
from hub.models.pathway import LearningPath, UserLearningPath


def make_teacher(username='teacher1'):
    user = User.objects.create_user(username=username, password='pass')
    UserProfile.objects.create(user=user, user_type=UserProfile.UserType.TEACHER)
    return user


def make_paths():
    LearningPath.objects.create(name='Beginner Foundations', slug='beginner-foundations', competency_min=0, competency_max=2)
    LearningPath.objects.create(name='Intermediate Growth', slug='intermediate-growth', competency_min=3, competency_max=4)
    LearningPath.objects.create(name='Advanced Integration', slug='advanced-integration', competency_min=5, competency_max=6)


def all_answers(value):
    """{question_id: value} for every active question."""
    return {q.id: value for q in OnboardingQuestion.objects.filter(is_active=True)}


class SelfEfficacyGetTests(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        self.client.force_authenticate(self.user)

    def test_returns_six_dimensions_with_four_questions_each(self):
        res = self.client.get(reverse('self-efficacy'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['dimensions']), 6)
        self.assertEqual(res.data['total'], 24)
        self.assertEqual(res.data['answered'], 0)
        self.assertFalse(res.data['completed'])
        for dim in res.data['dimensions']:
            self.assertEqual(len(dim['questions']), 4)
            self.assertEqual(set(dim['questions'][0].keys()), {'id', 'text'})

    def test_content_creator_forbidden(self):
        creator = User.objects.create_user(username='cc', password='pass')
        UserProfile.objects.create(user=creator, user_type=UserProfile.UserType.CONTENT_CREATOR)
        self.client.force_authenticate(creator)
        self.assertEqual(self.client.get(reverse('self-efficacy')).status_code, 403)

    def test_localized_to_user_language(self):
        dim = OnboardingDimension.objects.filter(is_active=True).first()
        dim.translations = {'el': 'Γνώση ΤΝ'}
        dim.save()
        q = dim.questions.first()
        q.translations = {'el': 'Ερώτηση'}
        q.save()
        self.user.profile.language = 'el'
        self.user.profile.save()
        res = self.client.get(reverse('self-efficacy'))
        found = next(d for d in res.data['dimensions'] if d['slug'] == dim.slug)
        self.assertEqual(found['name'], 'Γνώση ΤΝ')
        self.assertEqual(found['questions'][0]['text'], 'Ερώτηση')


class SelfEfficacyPostTests(APITestCase):
    def setUp(self):
        self.user = make_teacher()
        make_paths()
        self.client.force_authenticate(self.user)

    def test_partial_save_persists_and_does_not_complete(self):
        first = OnboardingQuestion.objects.filter(is_active=True).first()
        res = self.client.post(reverse('self-efficacy'), {'answers': {str(first.id): 4}}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data['completed'])
        self.assertEqual(res.data['answered'], 1)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.self_efficacy_answers[str(first.id)], 4)
        self.assertIsNone(self.user.profile.self_efficacy_completed_at)

    def test_resume_returns_saved_answers(self):
        first = OnboardingQuestion.objects.filter(is_active=True).first()
        self.client.post(reverse('self-efficacy'), {'answers': {str(first.id): 3}}, format='json')
        res = self.client.get(reverse('self-efficacy'))
        self.assertEqual(res.data['answers'][str(first.id)], 3)

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_full_high_completes_and_places_advanced(self, mock_task):
        res = self.client.post(reverse('self-efficacy'), {'answers': all_answers(5)}, format='json')
        self.assertTrue(res.data['completed'])
        self.assertEqual(res.data['overall_band'], 'high')
        for dim in res.data['dimensions']:
            self.assertEqual(dim['average'], 5.0)
            self.assertEqual(dim['band'], 'high')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.competency_score, 5)  # high → 5
        self.assertIsNotNone(self.user.profile.self_efficacy_completed_at)
        path = UserLearningPath.objects.get(user=self.user)
        self.assertEqual(path.path.slug, 'advanced-integration')
        mock_task.assert_called_once_with(self.user.id)

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_full_low_places_beginner(self, mock_task):
        res = self.client.post(reverse('self-efficacy'), {'answers': all_answers(1)}, format='json')
        self.assertEqual(res.data['overall_band'], 'low')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.competency_score, 1)  # low → 1

    @patch('hub.tasks.compute_user_recommendations.delay')
    def test_completing_in_two_batches(self, mock_task):
        answers = all_answers(4)
        ids = list(answers)
        half = {str(i): answers[i] for i in ids[:12]}
        rest = {str(i): answers[i] for i in ids[12:]}
        r1 = self.client.post(reverse('self-efficacy'), {'answers': half}, format='json')
        self.assertFalse(r1.data['completed'])
        r2 = self.client.post(reverse('self-efficacy'), {'answers': rest}, format='json')
        self.assertTrue(r2.data['completed'])
        self.assertEqual(r2.data['overall_band'], 'high')  # 4.0 → high

    def test_rating_out_of_range_rejected(self):
        first = OnboardingQuestion.objects.filter(is_active=True).first()
        res = self.client.post(reverse('self-efficacy'), {'answers': {str(first.id): 6}}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_question_rejected(self):
        res = self.client.post(reverse('self-efficacy'), {'answers': {'999999': 3}}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
